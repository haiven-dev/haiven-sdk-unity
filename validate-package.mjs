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
//   node csharp/unity/validate-package.mjs

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs"
import { dirname, join, relative, sep } from "node:path"
import { fileURLToPath } from "node:url"

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

// SemVer, with an optional prerelease such as 0.1.0-alpha.1. UPM treats a
// non-semver version as older than every real one. 0.0.0 stays valid in the
// manifest; ci/release.py refuses to tag that development sentinel.
check(
	/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/.test(manifest.version),
	`version is not semver: ${manifest.version}`,
)

// The minimum editor version is declared as MAJOR.MINOR with no patch. Unity
// rejects a three-part value here, which is easy to write and fails at import.
check(/^\d{4}\.\d+$/.test(manifest.unity), `unity must be MAJOR.MINOR: ${manifest.unity}`)

const asmdefs = files.filter((f) => f.endsWith(".asmdef"))
check(asmdefs.length === 1, `expected exactly one asmdef, found ${asmdefs.length}`)

for (const path of asmdefs) {
	const asmdef = JSON.parse(readFileSync(join(PACKAGE, path), "utf8"))
	const stem = path.split("/").pop().replace(/\.asmdef$/, "")

	// Unity keys the assembly by the `name` field and the file name has to
	// match it. When they differ the assembly builds under one name and is
	// referenced under the other, so every reference to it silently resolves to
	// nothing.
	check(asmdef.name === stem, `asmdef name ${asmdef.name} does not match its file ${stem}`)
	check(path.startsWith("Runtime/"), `asmdef is outside Runtime/: ${path}`)
}

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
	const source = readFileSync(join(PACKAGE, path), "utf8").replace(/\{\{\{[^}]*\}\}\}/g, "(function(){})")

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

console.error(`com.haiven.sdk: ${files.length} file(s), layout valid`)
console.error("NOT a substitute for opening the package in Unity — see csharp/unity/README.md")
