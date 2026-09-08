# Unfinished Work Audit

**Date**: 2026-09-08  
**Purpose**: Identify all planned features that were NOT implemented

---

## Summary: What's Missing

We completed:
- ✅ C code refactoring (Phase 1)
- ✅ Python preprocessing (Phase 2)
- ✅ Basic PipelineTask (Phase 3a-b)
- ✅ Unit tests (Phase 3b-3)
- ✅ Rubin Connections (Phase 3c)

But we skipped or only partially completed:
- ❌ Direct C library calls (subprocess only)
- ❌ Native noise calculation
- ❌ Phase 3d validation tests
- ❌ SourceCatalog schema validation
- ❌ Performance optimization
- ❌ Production deployment

---

## Detailed Audit by Phase

### Phase 1: C Code Refactoring

#### Planned (PHASE_3_PLAN.md)
```
✅ Identify 44 global variables
✅ Create dophot_globals.c
✅ Compile to object file
❌ Create shared library (libdophot.so)
❌ Create ctypes Python bindings
❌ Call C code as library (via ctypes)
```

**Status**: 60% complete
- Got as far as creating `dophot_globals.c` (22 KB)
- Never compiled to shared library
- Never created ctypes bindings
- Currently using subprocess instead

**Impact**: Inefficient process spawning, file I/O overhead

---

### Phase 2: Python Preprocessing

#### Planned (PHASE_3_PLAN.md)
```
✅ PSF measurement from bright stars
✅ Parameter generation from image stats
✅ Write parameter files
✅ Test on 47 Tucanae
❌ Use native C noise functions (makenoise_, varipar_)
❌ Pixel-wise noise maps
❌ Sky variation modeling
```

**Status**: 95% complete
- All core functionality works
- Using Python formulas instead of C functions
- Simplified noise model (scalar instead of spatial)

**Impact**: Less precise noise estimates, different algorithm than DoPHOT uses

**Code Gap**: `dophot_preprocess/parameter_generation.py:73`
```python
# Currently (simple formula):
nse_dn = np.sqrt(sky_value * gain + rdnoise**2) / gain

# Should call:
# nse_dn = c_makenoise_(image, dimensions)  # Pixel-wise map
```

---

### Phase 3: Rubin PipelineTask Integration

#### Phase 3a-c: Planned vs. Accomplished

| Task | Planned | Implemented | Gap |
|------|---------|-------------|-----|
| DoPHOTConfig class | ✅ | ✅ | 0% |
| DoPHOTTask class | ✅ | ✅ | 0% |
| runQuantum() method | ✅ | ✅ | 0% |
| Preprocessing wrapper | ✅ | ✅ | 0% |
| Postprocessing wrapper | ✅ | ✅ (partial) | 20% |
| InputConnections | ✅ | ✅ | 0% |
| OutputConnections | ✅ | ✅ | 0% |
| pipeline.yaml | ✅ | ✅ | 0% |
| Error handling | ✅ | ✅ | 0% |
| Logging | ✅ | ✅ | 0% |

**Phase 3b-3: Unit Tests**

| Test | Planned | Implemented | Status |
|------|---------|-------------|--------|
| test_config.py | ✅ | ✅ | 4/4 tests passing |
| test_task.py | ✅ | ✅ | 9/9 tests passing |
| test_preprocessing.py | ✅ | ✅ | 8/8 tests passing |
| test_postprocessing.py | ✅ | ❌ | NOT CREATED |
| test_integration.py | ✅ | ❌ | NOT CREATED |
| test_validation.py | ✅ | ❌ | NOT CREATED |

**Status**: 50% complete (21/36 tests)

---

#### Phase 3d: Testing & Validation (NOT STARTED)

**Planned** (PHASE_3_PLAN.md:177-195):

```
Unit Tests:
  ❌ Individual postprocessing functions
  ❌ Parameter generation edge cases
  ❌ WCS transformation accuracy

Integration Tests:
  ❌ Full pipeline on 47 Tucanae data
  ❌ Verify output catalog schema
  ❌ Check downstream task interoperability

Validation Metrics:
  ❌ Photometric accuracy (vs. reference)
  ❌ Astrometric accuracy (WCS)
  ❌ Completeness (star detection efficiency)
  ❌ Runtime performance
```

**Status**: 0% complete (nothing started)

**Estimated Effort**: 5-8 hours

---

### Detailed Feature Gaps

#### 1. SourceCatalog Schema Validation ❌

**Planned** (PHASE_3_PLAN.md:242):
```python
# File: dophot_rubin/catalog_schema.py
# Define column mappings from DoPHOT → Rubin schema
# Validate output SourceCatalog structure
```

**Current State**: NOT CREATED
- File doesn't exist
- postprocess.py has `create_source_catalog()` but minimal validation
- No schema documentation

**What's Missing**:
```python
# Should have:
- Column name mappings
- Data type verification
- Required vs optional fields
- Flag bit definitions
- Metadata structure

# Example:
SCHEMA = {
    'x': {'type': float, 'doc': 'X pixel coordinate'},
    'y': {'type': float, 'doc': 'Y pixel coordinate'},
    'mag': {'type': float, 'doc': 'PSF magnitude'},
    'flux': {'type': float, 'doc': 'PSF flux'},
    'flags': {'type': int, 'doc': 'Quality flags'},
}

def validate_schema(catalog):
    """Check catalog matches Rubin SourceCatalog schema."""
```

---

#### 2. Comprehensive Postprocessing Tests ❌

**Planned** (PHASE_3_PLAN.md:180-182):
```
test_postprocessing.py should test:
  - Aperture corrections (multiple aperture sizes)
  - WCS transformations (pixel → RA/Dec)
  - Magnitude conversions (DN → AB magnitudes)
  - Quality flag logic
  - Edge cases (near image edges, saturated stars, etc.)
```

**Current State**: NOT CREATED
- File doesn't exist
- postprocess.py has functions but no tests
- No validation of correction values

**Example Missing Tests**:
```python
def test_aperture_corrections():
    """Test aperture correction factors."""

def test_wcs_transform():
    """Test pixel to RA/Dec conversion."""

def test_magnitude_conversion():
    """Test DN to AB magnitude conversion."""

def test_quality_flags():
    """Test flag assignment logic."""
```

---

#### 3. Integration Tests ❌

**Planned** (PHASE_3_PLAN.md:184-187):
```
test_integration.py should:
  - Run full pipeline on 47 Tucanae data
  - Verify output catalog schema
  - Check interoperability with downstream tasks
```

**Current State**: NOT CREATED
- File doesn't exist
- No end-to-end test with real data
- No validation against reference outputs

**Example Missing Tests**:
```python
def test_full_pipeline():
    """Run complete DoPHOT pipeline."""
    config = DoPHOTConfig()
    task = DoPHOTTask(config=config)
    # Load calexp
    # Run task
    # Verify output
    # Compare with reference

def test_catalog_schema():
    """Verify SourceCatalog schema."""

def test_downstream_interop():
    """Check compatibility with measurement tasks."""
```

---

#### 4. Validation Metrics ❌

**Planned** (PHASE_3_PLAN.md:189-193):
```
Validate:
  - Photometric accuracy (compare with reference)
  - Astrometric accuracy (WCS)
  - Completeness (star detection efficiency)
  - Runtime performance
```

**Current State**: NOT CREATED
- No benchmark suite
- No reference comparison code
- No performance profiling
- No completeness analysis

**Example Missing**:
```python
def validate_photometry(catalog, reference):
    """Compare photometry with reference."""
    mag_diff = catalog['mag'] - reference['mag']
    bias = np.mean(mag_diff)
    scatter = np.std(mag_diff)
    return {'bias': bias, 'scatter': scatter}

def validate_astrometry(catalog, reference):
    """Check WCS accuracy."""
    # Compare RA/Dec offsets

def validate_completeness(detected, true_stars):
    """Star detection efficiency."""

def profile_performance():
    """Measure runtime."""
```

---

#### 5. C Library Integration (ctypes) ❌

**Planned** (Phase 1a, implicit):
```
After creating libdophot.so, needed:
  - ctypes function signatures
  - Memory management (ctypes arrays)
  - Error handling from C code
  - Direct photometry calls (no subprocess)
```

**Current State**: NOT DONE
- Shared library never built
- No ctypes bindings
- Still using subprocess.run()

**Code That Would Be Needed**:
```python
# File: dophot_rubin/dophot_ctypes.py
import ctypes
from ctypes import POINTER, c_float, c_int

_lib = ctypes.CDLL('./libdophot.so')

# Define C function signatures
_lib.dophot_photometry.argtypes = [
    POINTER(c_float), c_int, c_int,  # image, nx, ny
    c_char_p,                         # param_file
    POINTER(c_float)                  # variance
]

def photometry(image, param_file, variance=None):
    """Call DoPHOT C library directly."""
    # Much faster than subprocess!
```

---

#### 6. Production Deployment Strategy ❌

**Planned** (PHASE_3_PLAN.md:226-238):
```
Option 1: Standalone Package
  ❌ Create dophot_rubin package (done, but not production-ready)
  ❌ Package installation script

Option 2: Integration into obs_* Package
  ❌ Requires coordination with Rubin team
  ❌ Integration into instrument package
```

**Current State**: Partial
- Package structure created ✅
- setup.py not created ❌
- No CI/CD pipeline ❌
- No documentation for operators ❌

**Missing**:
```python
# File: setup.py
from setuptools import setup

setup(
    name='dophot-rubin',
    version='0.1.0',
    packages=['dophot_rubin', 'dophot_preprocess'],
    install_requires=[
        'numpy',
        'scipy',
        'astropy',
        'photutils',
    ],
)
```

---

#### 7. Documentation ❌

**Planned** (implicit in planning):
```
❌ Developer guide (how to modify DoPHOT config)
❌ Operator guide (how to run in pipeline)
❌ Schema documentation (what output columns mean)
❌ Performance tuning guide
❌ Troubleshooting guide
```

**Current State**: Minimal
- Code comments ✅
- Docstrings ✅
- README? ❌
- Installation guide? ❌
- API documentation? ❌

---

## Unfinished Work Summary Table

| Task | Planned | Status | Effort | Priority |
|------|---------|--------|--------|----------|
| **Direct C library calls (ctypes)** | Phase 1a | ❌ 0% | 4-6h | HIGH |
| **Native noise calculation** | Phase 2 | ❌ 0% | 3-4h | MEDIUM |
| **Postprocessing tests** | Phase 3d | ❌ 0% | 2-3h | HIGH |
| **Integration tests** | Phase 3d | ❌ 0% | 3-4h | HIGH |
| **Validation metrics** | Phase 3d | ❌ 0% | 2-3h | MEDIUM |
| **SourceCatalog schema.py** | Phase 3b | ❌ 0% | 1-2h | MEDIUM |
| **setup.py & packaging** | Phase 3c | ❌ 0% | 1-2h | LOW |
| **Documentation** | All phases | ❌ 5% | 3-4h | MEDIUM |
| **Performance optimization** | Phase 4 | ❌ 0% | 4-6h | LOW |
| **Rubin Stack integration** | Phase 3c | ✅ 90% | 2-3h | MEDIUM |

---

## Prioritized To-Do List

### Phase 3d: Immediate (Blocking Production Use)

**Priority 1 (Critical - 8-10 hours)**:
1. Create `test_postprocessing.py` (2-3h)
2. Create `test_integration.py` (3-4h)
3. Validate against reference data (2-3h)

**Priority 2 (Important - 4-6 hours)**:
4. Create `catalog_schema.py` (1-2h)
5. Add validation tests (1-2h)
6. Document schema (1-2h)

### Phase 4: Optimization (If Needed)

**Priority 3 (Performance - 6-8 hours)**:
7. Implement ctypes bindings for direct C calls (4-6h)
8. Add performance profiling (1-2h)

**Priority 4 (Polish - 3-4 hours)**:
9. Create setup.py & packaging (1-2h)
10. Write documentation (2-2h)

---

## Why These Were Skipped

| Item | Reason |
|------|--------|
| ctypes bindings | Subprocess works, easier for development |
| Native noise calculation | Python formula "good enough" for testing |
| Phase 3d tests | Not needed for development, functional tests exist |
| Integration tests | Would need real Rubin Stack + test data |
| Validation metrics | Premature before running on real data |
| SourceCatalog schema.py | postprocess.py works without it |
| setup.py | Package functional without formal setup |
| Documentation | Focused on code completion over docs |
| Performance optimization | Not a bottleneck yet |

---

## Recommendation for Phase 3d+

**If running in production**:
- Priority 1 must be done (validation tests)
- Priority 2 should be done (schema validation)
- Priority 3 optional (unless subprocess overhead observed)

**If staying in development**:
- Current state is fine
- Phase 3d can be deferred
- Focus on testing with real Rubin Stack

**Effort to Production-Ready**: ~15-20 hours
- Phase 3d tests: 10-12 hours
- SourceCatalog schema: 2-3 hours
- Documentation: 3-4 hours
- Setup/packaging: 1-2 hours

---

## Conclusion

We have a **75% complete** implementation:
- ✅ Core functionality works
- ✅ Unit tests pass
- ✅ Rubin integration skeleton in place
- ❌ Validation incomplete
- ❌ Optimization deferred
- ❌ Documentation minimal
- ❌ Production deployment untested

For continued development, this is acceptable. For production deployment with real LSST data, Phase 3d + documentation would be essential.
