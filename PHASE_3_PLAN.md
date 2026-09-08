# Phase 3: Rubin PipelineTask Integration

**Objective**: Create a Rubin-compatible PipelineTask that orchestrates DoPHOT processing within the LSST pipeline.

**Status**: Planning (3a) → Implementation (3b) → Integration (3c) → Testing (3d)

---

## Phase 3a: Task Architecture & Design

### Workflow

```
Input: calexp (calibrated exposure from reprocessVisitImage)
         ↓
  [Python Preprocessing]
  - Extract image, variance, mask from DP2 FITS
  - Measure PSF from bright stars
  - Generate DoPHOT parameters
  - Write parameter file
         ↓
  [C DoPHOT Library Call]
  - Execute DoPHOT with parameter file
  - Read source catalog output
         ↓
  [Python Postprocessing]
  - Aperture corrections
  - WCS transformation (pixel → RA/Dec)
  - Convert to AB magnitudes
  - Write SourceCatalog
         ↓
Output: src (SourceCatalog with DoPHOT photometry)
```

### Rubin PipelineTask Structure

#### Required Classes

**1. DoPHOTConfig** (pexConfig.Config)
```python
class DoPHOTConfig(pexConfig.Config):
    # Input/output configuration
    # Algorithm parameters
    # File paths for DoPHOT C executable
```

**2. DoPHOTTask** (pipe.base.PipelineTask)
```python
class DoPHOTTask(pipe.base.PipelineTask):
    ConfigClass = DoPHOTConfig
    _DefaultName = "dophot"
    
    def runQuantum(self, butlerQC, inputRefs, outputRefs):
        # Execute per-dataId (per-visit-per-detector)
        # Call preprocessing → DoPHOT → postprocessing
```

#### Data Connections

**Inputs**:
- `calexp`: Calibrated exposure (DP2 FITS with IMAGE/MASK/VARIANCE extensions)
- `skyMap`: Sky map (for WCS)
- `photoCalib`: Photometric calibration (for magnitude conversion)
- `psf`: PSF model (from reprocessVisitImage)

**Outputs**:
- `src`: SourceCatalog with DoPHOT photometry
- `srcMetadata`: Metadata (PSF sigma, parameters used, etc.)

#### Configuration Options

```python
# PSF measurement
psfDetectionThreshold = 10.0  # sigma above sky for bright stars
psfMinStars = 20              # minimum successful PSF measurements

# DoPHOT execution
doPHOTExecPath = "/path/to/dophot"  # Path to DoPHOT executable
useEmpiricalModel = True            # Use empirical PSF model

# Postprocessing
apertureRadius = 2.0          # Aperture radius (arcsec)
doApertureCorrection = True   # Apply aperture corrections
doWcsTransform = True         # Transform to RA/Dec
```

---

## Phase 3b: Implementation Tasks

### Task 3b-1: Create Config & Task Classes
**Effort**: 2-3 hours
- Define DoPHOTConfig with all configurable parameters
- Implement DoPHOTTask skeleton
- Define input/output connections

### Task 3b-2: Implement runQuantum()
**Effort**: 3-4 hours
- Load calexp data
- Extract IMAGE/MASK/VARIANCE extensions
- Call preprocessing pipeline
- Execute DoPHOT C code
- Parse output catalogs
- Call postprocessing

### Task 3b-3: Create Preprocessor Wrapper
**Effort**: 1-2 hours
- Wrap existing Python preprocessing for task context
- Handle temporary files
- Logging/error handling

### Task 3b-4: Create Postprocessor
**Effort**: 2-3 hours
- Aperture photometry corrections
- WCS transformation (pixel → RA/Dec)
- AB magnitude conversion
- Convert to SourceCatalog schema

### Task 3b-5: Error Handling & Logging
**Effort**: 1-2 hours
- Graceful failures (no PSF measurement, DoPHOT errors)
- Logging at each stage
- Metadata tracking

---

## Phase 3c: Integration with Rubin Stack

### Required Knowledge

**1. SourceCatalog Schema**
- Standard Rubin source table format
- Required vs. optional columns
- Measurement flags

**2. Butler I/O**
- Reading calexp from Butler
- Writing src catalogs
- Metadata storage

**3. Task Connections**
- Defining InputConnections/OutputConnections
- PrerequisiteTasks (depends on prior tasks)
- Dataset types

**4. Configuration Management**
- Config overrides
- Defaults in pipeline.yaml
- Per-detector/per-visit overrides

### Integration Steps

1. **Register dataset types** (in obs_* package or registry)
   - If creating new types for DoPHOT output

2. **Add to pipeline.yaml**
   ```yaml
   tasks:
     dophot:
       class: lsst.ip.isr.DoPHOTTask
       config:
         psfDetectionThreshold: 10.0
         useEmpiricalModel: true
       inputs:
         calexp: IsrTask.postISRCCD
       outputs:
         src: dophot_src
   ```

3. **Test in pipeline context**
   - Run on test data through Butler
   - Validate output schemas
   - Check interoperability with downstream tasks

---

## Phase 3d: Testing & Validation

### Unit Tests
- Individual preprocessing functions (already done in Phase 2d)
- Postprocessing functions
- Parameter generation edge cases

### Integration Tests
- Full pipeline on 47 Tucanae data
- Verify output catalog schema
- Compare with reference outputs

### Validation Metrics
- Photometric accuracy (compare with reference)
- Astrometric accuracy (WCS)
- Completeness (star detection efficiency)
- Runtime performance

---

## Technology Stack

### Rubin Libraries (when available)
```
lsst.pipe.base          # PipelineTask framework
lsst.pex.config         # Configuration
lsst.daf.butler         # Data I/O
lsst.afw.image          # Image handling
lsst.afw.catalog        # SourceCatalog
lsst.afw.geom           # Geometric transformations
lsst.geom               # Geometry utilities
```

### Our Code
```
dophot_preprocess       # PSF measurement + parameter generation
dophot_task             # Rubin PipelineTask wrapper
dophot_postprocess      # Aperture corrections + WCS + magnitudes
```

### External Dependencies
```
numpy, scipy            # Scientific computing
astropy                 # FITS I/O, WCS
photutils              # Star detection (already in pipeline)
```

---

## Deployment Strategy

### Option 1: Standalone Package
- Create `dophot_rubin` package
- Can be installed alongside Rubin Stack
- Minimal dependencies on LSST internals

### Option 2: Integration into obs_* Package
- Add to instrument-specific package (e.g., obs_lsst)
- Fully integrated into pipeline
- Requires coordination with Rubin team

**Recommendation**: Start with Option 1 (standalone), can migrate to Option 2 later.

---

## Files to Create (Phase 3b-d)

```
dophot_rubin/
├── __init__.py
├── config.py                # DoPHOTConfig
├── task.py                  # DoPHOTTask
├── preprocess_wrapper.py    # Wrapper around dophot_preprocess
├── postprocess.py           # Aperture corrections, WCS, magnitudes
├── catalog_schema.py        # SourceCatalog column definitions
└── tests/
    ├── test_task.py         # Unit tests
    ├── test_integration.py  # Full pipeline tests
    └── test_validation.py   # Accuracy validation

setup.py                     # Package installation
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Rubin Stack not available | Create mock/template, can integrate later |
| SourceCatalog schema mismatch | Study existing tasks, follow conventions |
| DoPHOT failures on some images | Graceful fallback, flagging in metadata |
| Performance issues | Profile preprocessing, consider parallelization |
| WCS transformation accuracy | Validate against calexp WCS, unit tests |

---

## Timeline Estimate

- **Phase 3a (Planning)**: 1-2 hours ✓ (this document)
- **Phase 3b (Implementation)**: 10-15 hours
  - 3b-1: Task classes (2-3h)
  - 3b-2: runQuantum (3-4h)
  - 3b-3: Preprocessing wrapper (1-2h)
  - 3b-4: Postprocessing (2-3h)
  - 3b-5: Error handling (1-2h)
- **Phase 3c (Integration)**: 5-10 hours (depends on Rubin Stack availability)
- **Phase 3d (Testing)**: 5-8 hours

**Total Phase 3**: 20-35 hours (depending on Rubin Stack access)

---

## Success Criteria

✅ Task implements PipelineTask interface correctly  
✅ Handles all required input/output connections  
✅ Runs successfully on 47 Tucanae test data  
✅ Output SourceCatalog has correct schema  
✅ Photometry validated against reference  
✅ Integration with pipeline.yaml works  
✅ Graceful error handling for edge cases  

---

## Next Steps

1. **Phase 3b-1**: Create `dophot_rubin/config.py` and task skeleton
2. Check for Rubin Stack access (for importing pipeline classes)
3. Implement preprocessing wrapper
4. Implement postprocessing functions
5. Create integration tests

**Recommend**: Start with Phase 3b-1 (task structure) to establish framework.
