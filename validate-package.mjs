#!/usr/bin/env node
// Check the UPM package against the rules Unity would enforce, since Unity is
// not here to enforce them.
//
// There is no Unity installation in this repository, so the package layout is
// written from documented conventions and cannot be opened to see whether it
// works. That is a real gap and it is recorded as one — but the half of it that
// is mechanical does not need Unity at all. A package name that breaks UPM's
// naming rule, an asmdef whose name does not match its file, a `.jslib` outside
// a `Plugins` folder: each of those is a rule with one right answer, and each
// fails at import time with a message that does not name the file.
//
// So this validates what is checkable and stays quiet about what is not. It is
// not a substitute for opening the package in Unity, and the README says so.
//
//   node validate-package.mjs

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs"
import { dirname, join, relative, sep } from "node:path"
import { fileURLToPath } from "node:url"

import { isValidPackageVersion } from "./ci/package-version.mjs"

// URL.pathname on Windows is `/C:/...`. Joining that yields `\C:\...`, which
// opens as `C:\C:\...`. fileURLToPath returns a path the filesystem accepts.
const HERE = dirname(fileURLToPath(import.meta.url))
const PACKAGE = join(HERE, "com.haiven.sdk")

const problems = []
const check = (condition, message) => {
	if (!condition) problems.push(message)
}

/** Every file under the package, so a rule can be stated over the whole tree. */
function walk(dir, found = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) walk(path, found)
		// Checks below split on `/`. Windows join uses `\`, so normalize here.
		else found.push(relative(PACKAGE, path).split(sep).join("/"))
	}

	return found
}

const files = walk(PACKAGE)
const manifest = JSON.parse(readFileSync(join(PACKAGE, "package.json"), "utf8"))

// UPM requires a reverse-domain name, lower case, and the folder must match it.
// A mismatch imports as a package with a different identity than its folder,
// which resolves but cannot be referenced by name.
check(/^[a-z0-9][a-z0-9-_]*(\.[a-z0-9][a-z0-9-_]*)+$/.test(manifest.name), `package name is not a valid UPM name: ${manifest.name}`)
check(manifest.name === "com.haiven.sdk", `package folder and package name disagree: ${manifest.name}`)

for (const field of ["version", "displayName", "description", "unity"]) {
	check(typeof manifest[field] === "string" && manifest[field] !== "", `package.json is missing ${field}`)
}

// UPM sorts package versions according to SemVer, including prerelease versions.
// Reject malformed identifiers instead of silently sorting them unpredictably.
check(isValidPackageVersion(manifest.version), `version is not valid semver: ${manifest.version}`)

// Haiven's package source is Apache-2.0. The identifier has to match the
// LICENSE file that ships inside the package, because the UPM tarball does
// not include the repository-root copy.
check(manifest.license === "Apache-2.0", `package.json license must be Apache-2.0, found ${manifest.license}`)
const licensePath = join(PACKAGE, "LICENSE")
check(existsSync(licensePath), "package has no LICENSE")
if (existsSync(licensePath)) {
	const license = readFileSync(licensePath, "utf8")
	check(license.includes("Apache License") && license.includes("Version 2.0, January 2004"), "package LICENSE is not Apache-2.0")
}

// The minimum editor version is declared as MAJOR.MINOR with no patch. Unity
// rejects a three-part value here, which is easy to write and fails at import.
check(/^\d{4}\.\d+$/.test(manifest.unity), `unity must be MAJOR.MINOR: ${manifest.unity}`)

// The package compiles on its own: the core as source in its own assembly, the
// Unity bridge over it, the WebRTC transport, an editor-only assembly, and test
// assemblies that only exist when a project lists the package in `testables`.
// The NGO sample is not compiled until a game imports it from Samples~.
const EXPECTED_ASMDEFS = {
	"Runtime/Haiven.Sdk.asmdef": "runtime",
	"Runtime/Core/Haiven.Sdk.Core.asmdef": "core",
	"Runtime/WebRtc/Haiven.Sdk.WebRtc.asmdef": "webrtc",
	"Samples~/Netcode/Haiven.Sdk.Samples.Netcode.asmdef": "sample",
	"Tests/WebRtc/Haiven.Sdk.Tests.WebRtc.asmdef": "test",
	"Tests/WebRtcRelay/Haiven.Sdk.WebRtc.RelayTests.asmdef": "test",
	"Runtime/SystemTextJson/Haiven.Sdk.SystemTextJson.Unity.asmdef": "optional-json",
	"Editor/Haiven.Sdk.Editor.asmdef": "editor",
	"Tests/Editor/Haiven.Sdk.Tests.Editor.asmdef": "test",
	"Tests/Runtime/Haiven.Sdk.Tests.Runtime.asmdef": "test",
}
const asmdefs = files.filter((f) => f.endsWith(".asmdef"))
check(
	JSON.stringify([...asmdefs].sort()) === JSON.stringify(Object.keys(EXPECTED_ASMDEFS).sort()),
	`asmdefs are ${asmdefs.join(", ")}; expected ${Object.keys(EXPECTED_ASMDEFS).join(", ")}`,
)
for (const path of asmdefs) {
	const asmdef = JSON.parse(readFileSync(join(PACKAGE, path), "utf8"))
	const stem = path.split("/").pop().replace(/\.asmdef$/, "")
	// Unity keys the assembly by the `name` field and the file name has to
	// match it. When they differ the assembly builds under one name and is
	// referenced under the other, so every reference to it silently resolves to
	// nothing.
	check(asmdef.name === stem, `asmdef name ${asmdef.name} does not match its file ${stem}`)

	// The hand-published DLL this package used to expect. Referencing it again
	// would bring back the manual install step.
	check(
		!(asmdef.precompiledReferences ?? []).includes("Haiven.Sdk.Core.dll"),
		`${path} references Haiven.Sdk.Core.dll; the core ships as source in Runtime/Core`,
	)

	const kind = EXPECTED_ASMDEFS[path]
	if (kind === "core") {
		check(asmdef.noEngineReferences === true, `${path} must stay engine-free (noEngineReferences)`)
	}
	if (kind === "runtime" || kind === "editor" || kind === "optional-json" || kind === "webrtc" || kind === "sample") {
		check((asmdef.references ?? []).includes("Haiven.Sdk.Core"), `${path} must reference Haiven.Sdk.Core`)
	}
	if (kind === "optional-json") {
		check(
			(asmdef.defineConstraints ?? []).includes("HAIVEN_SDK_SYSTEM_TEXT_JSON"),
			`${path} must remain an explicit System.Text.Json opt-in`,
		)
		check(
			JSON.stringify(asmdef.precompiledReferences ?? []) === JSON.stringify(["System.Text.Json.dll"]),
			`${path} must reference only the explicitly staged System.Text.Json assembly`,
		)
	}
	// com.unity.webrtc has no WebGL runtime. The transport, its tests and the
	// sample over it stay out of a WebGL build, which keeps the WebSocket SDK.
	if (kind === "webrtc" || kind === "sample" || path.startsWith("Tests/WebRtc")) {
		check((asmdef.excludePlatforms ?? []).includes("WebGL"), `${path} must exclude WebGL`)
	}
	if (kind === "webrtc") {
		check((asmdef.references ?? []).includes("Unity.WebRTC"), `${path} must reference Unity.WebRTC`)
	}
	if (kind === "sample") {
		check((asmdef.references ?? []).includes("Unity.Netcode.Runtime"), `${path} must reference Unity.Netcode.Runtime`)
	}
	if (kind === "editor") {
		check(
			JSON.stringify(asmdef.includePlatforms) === JSON.stringify(["Editor"]),
			`${path} must be editor-only`,
		)
	}
	if (kind === "test") {
		// Without the constraint a test assembly compiles into every consumer's
		// project; with it, only into projects that list the package in testables.
		check((asmdef.defineConstraints ?? []).includes("UNITY_INCLUDE_TESTS"), `${path} lacks UNITY_INCLUDE_TESTS`)
		check(asmdef.autoReferenced === false, `${path} must not be auto-referenced`)
	}
}

// Installing the SDK installs the WebRTC library its transport is built on. NGO
// stays out: only the sample needs it, and a game imports the sample on request.
check(manifest.dependencies?.["com.unity.webrtc"] === "3.0.0", "package.json must depend on com.unity.webrtc 3.0.0")
check(
	!Object.keys(manifest.dependencies ?? {}).some((name) => name.startsWith("com.unity.netcode")),
	"package.json must not depend on Netcode; the NGO adapter is a sample",
)
for (const sample of manifest.samples ?? []) {
	check(
		typeof sample.path === "string" && sample.path.startsWith("Samples~/") && existsSync(join(PACKAGE, sample.path)),
		`sample path does not exist under Samples~: ${sample.path}`,
	)
	check(typeof sample.displayName === "string" && sample.displayName !== "", `sample ${sample.path} has no displayName`)
}

// A git-URL package is immutable, and Unity ignores any asset in an immutable
// folder that has no .meta. scripts/vendor-unity.py writes them; this checks
// none went missing and none is orphaned, independently of that script.
const isAsset = (path) => !path.split("/").some((part) => part.startsWith(".") || part.endsWith("~"))
const assets = new Set()
for (const path of files.filter((f) => !f.endsWith(".meta") && isAsset(f))) {
	const parts = path.split("/")
	for (let i = 1; i <= parts.length; i++) assets.add(parts.slice(0, i).join("/"))
}
for (const asset of assets) {
	check(files.includes(`${asset}.meta`), `no .meta for ${asset}; run \`make vendor-unity\``)
}
for (const meta of files.filter((f) => f.endsWith(".meta"))) {
	check(assets.has(meta.replace(/\.meta$/, "")), `orphaned ${meta}`)
}
const guids = files
	.filter((f) => f.endsWith(".meta"))
	.map((f) => /^guid: ([0-9a-f]{32})$/m.exec(readFileSync(join(PACKAGE, f), "utf8"))?.[1])
check(!guids.includes(undefined), "a .meta has no 32-hex guid")
check(new Set(guids).size === guids.length, "two .meta files share a guid")

// The release package defaults to BuiltInJsonCodec and carries no managed
// binaries. The source-checkout-only System.Text.Json staging command must not
// leak its local output into a committed git-URL package.
const dlls = files.filter((f) => f.endsWith(".dll"))
check(dlls.length === 0, `the default package must not bundle managed DLLs: ${dlls.join(", ")}`)
check(
	!files.includes("Runtime/SystemTextJson/THIRD_PARTY_NOTICES.md"),
	"optional binary notices exist without an opt-in binary closure",
)

// documentationUrl has pointed at a moved README before. It must name this
// package's README on main, and the editor's Help menu must open the same page.
const REPOSITORY = "https://github.com/haiven-dev/haiven-sdk-unity/blob/main/"
check(
	manifest.documentationUrl === `${REPOSITORY}com.haiven.sdk/README.md`,
	`documentationUrl is not this package's README: ${manifest.documentationUrl}`,
)
check(
	readFileSync(join(PACKAGE, "Editor/HaivenSdkMenu.cs"), "utf8").includes(`"${manifest.documentationUrl}"`),
	"Editor/HaivenSdkMenu.cs DocumentationUrl differs from package.json documentationUrl",
)

// A `.jslib` is compiled into the WebGL build only when Unity recognises it as a
// WebGL plugin. Inside a package that recognition comes from the path — a
// `Plugins` folder — because a package's `.meta` files are generated on import
// and cannot be authored here to say it another way.
for (const path of files.filter((f) => f.endsWith(".jslib"))) {
	check(
		path.split("/").includes("Plugins") && path.split("/").includes("WebGL"),
		`.jslib must live under Plugins/WebGL to be picked up as a WebGL plugin: ${path}`,
	)
}

// link.xml has to be inside the package for IL2CPP to find it, and there should
// be exactly one — two are not merged in any documented order.
const links = files.filter((f) => f.endsWith("link.xml"))
check(links.length === 1, `expected exactly one link.xml, found ${links.length}`)
if (links.length === 1) {
	const link = readFileSync(join(PACKAGE, links[0]), "utf8")
	check(link.includes('assembly fullname="Haiven.Sdk"'), "link.xml must preserve the WebGL callback assembly")
	check(!link.includes('assembly fullname="Haiven.Sdk.Core"'), "link.xml must not preserve reflection-free core")
}

check(existsSync(join(PACKAGE, "README.md")), "package has no README.md")

// A `.jslib` is JavaScript, and a syntax error in one is reported by emscripten
// at link time as a build failure with no file or line. Parsing it here is the
// cheapest thing that turns that into a message naming the file.
//
// The `{{{ ... }}}` are emscripten preprocessor macros rather than JavaScript,
// so they are substituted the way the toolchain substitutes them — with a call —
// before parsing. That checks the surrounding code and deliberately does not
// check the macro, which only emscripten can resolve.
for (const path of files.filter((f) => f.endsWith(".jslib"))) {
	const rawSource = readFileSync(join(PACKAGE, path), "utf8")
	check(
		!/\)\s*\n\s*\{\{\{/.test(rawSource),
		`${path} has a call immediately before an emscripten macro without a semicolon`,
	)
	const source = rawSource.replace(/\{\{\{[^}]*\}\}\}/g, "(function(){})")

	try {
		new Function("mergeInto", "LibraryManager", source)
	} catch (error) {
		check(false, `${path} is not parseable JavaScript: ${error.message}`)
	}
}

if (problems.length > 0) {
	for (const problem of problems) console.error(`invalid: ${problem}`)
	process.exit(1)
}

console.error(`com.haiven.sdk: ${files.length} file(s), ${asmdefs.length} asmdefs, ${dlls.length} DLLs, layout valid`)
console.error("NOT a substitute for opening the package in Unity — see host/README.md")
