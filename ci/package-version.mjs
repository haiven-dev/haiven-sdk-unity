const numericIdentifier = "(?:0|[1-9]\\d*)"
const nonNumericIdentifier = "(?:\\d*[A-Za-z-][0-9A-Za-z-]*)"
const prereleaseIdentifier = `(?:${numericIdentifier}|${nonNumericIdentifier})`
const buildIdentifier = "[0-9A-Za-z-]+"

const packageVersion = new RegExp(
	`^${numericIdentifier}\\.${numericIdentifier}\\.${numericIdentifier}` +
		`(?:-${prereleaseIdentifier}(?:\\.${prereleaseIdentifier})*)?` +
		`(?:\\+${buildIdentifier}(?:\\.${buildIdentifier})*)?$`,
)

export const isValidPackageVersion = (version) => typeof version === "string" && packageVersion.test(version)
