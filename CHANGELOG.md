# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2023-05-31

### Added

- Move connection breakdown logic from datamodel to pce (#96)
- Code formatting checks on CI (#74)
- Cache dependencies on CI (#53)
- Code coverage reporting with coveralls.io (#51)

### Fixed

- Add domains in path breakdowns (#111, #113, #115)
- Add error checks to `TEManager` (#108)

### Changed

- Update README (#91)
- Refactor connection breakdown logic (#98)
- Update solver output (#93)
- Make pygraphviz an optional dependency (#90)
- Refactor tests (#88)
- Rename modules, classes, and methods to be PEP8-compliant (#84)
- Stricter linting on CI (#75)
- Module organization updates (#79)
- Re-write of PCE functions (#50, #22, #45, #47, #48)

### Removed

- Remove unused `weight_assign` (#89)
- Remove old PCE functions (#83)

## [1.0.0] - 2022-06-22

No Changelog entries available.


[2.0.0]: https://github.com/atlanticwave-sdx/pce/compare/1.0.0...2.0.0
[1.0.0]: https://github.com/atlanticwave-sdx/pce/compare/60af115...1.0.0
