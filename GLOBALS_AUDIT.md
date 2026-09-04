# DoPHOT C Code: Global Variables Audit

**Date**: 2026-09-04  
**Status**: Phase 1a Planning  
**Total Global Variables**: 43 structs + 1 FILE pointer = **44 globals**

---

## Global Struct Variables (43 total)

These are defined directly in `structs/*_struct.h` files and included everywhere:

### Configuration Structs (tune*)
1. `tune1_` — PSF FWHM parameters
2. `tune2_` — Box size parameters
3. `tune3_` — Threshold parameters
4. `tune4_` — Fitting iteration parameters
5. `tune5_` — Noise parameters
6. `tune6_` — Object subtraction parameters
7. `tune7_` — PSF symmetry parameters
8. `tune8_` — Shape discrimination parameters
9. `tune9_` — Quality control parameters
10. `tune10_` — Pixel sufficiency parameters
11. `tune11_` — Gain/readout noise parameters
12. `tune12_` — Mask box parameters
13. `tune13_` — Edge trimming parameters
14. `tune14_` — Logging verbosity parameter
15. `tune15_` — Fitting accuracy parameters
16. `tune16_` — File flags parameters
17. `tune17_` — PSF shape parameters
18. `tune18_` — Pixel threshold parameters
19. `tune19_` — Aperture magnitude error parameters
20. `tune20_` — Median filter parameters
21. `tune21_` — Position fixing parameters
22. `tune22_` — Empirical model parameters
23. `tune23_` — Empirical skip parameters

### Working Storage Structs (non-tune)
24. `addobj_` — Star subtraction boundaries
25. `aperlist_` — Aperture list data
26. `byvirtue_` — Chi-squared terms
27. `changed_` — Change tracking
28. `clobber_` — Clobbering flag
29. `crudestat_` — Crude statistics
30. `ctimes_` — CPU timing data
31. `dfake_`, `odfake_` — Fake derivatives
32. `drfake_` — Derivative flag
33. `efake_`, `oefake_` — Error fake values
34. `empmom_`, `estuff_` — Empirical model data
35. `eoff_` — Empirical offset
36. `fitarrays_` — Fitting arrays
37. `fitting_matrices_` — Matrix storage for fits
38. `fixpass_`, `funnypass_`, `galpass_` — Pass flags
39. `free_parking_` — Temporary storage arrays
40. `hubvar_`, `skyvar_` — Sky model parameters
41. `imdev_`, `oimdev_` — Image deviation storage
42. `median_` — Median filter storage
43. `model_` — Model tracking
44. `passweird_`, `passmask_`, `passimp_` — Pass flags
45. `pqfake_`, `opqfake_`, `rsfake_`, `orsfake_` — Fake parameters
46. `pararray_`, `parpred_` — Parameter arrays
47. `probpass_` — Probability storage
48. `search_` — Search parameters
49. `starlist_` — Star list storage
50. `subraster_` — Subraster data
51. `trans7_` — Transformation flag
52. `undergnd_` — Underground parameters
53. `unitize_` — Unit scaling factor

### Special Variables
- `logfile` (FILE*) — Log file handle

---

## Current Problem

**Issue**: All globals defined directly in headers
- Each header is included in multiple `.c` files
- Linker sees multiple definitions → **linker errors**
- Cannot create shared library with multiple definition symbols
- Makes library non-reentrant (can't call multiple times safely)

---

## Refactoring Strategy

### Phase 1: Conversion to extern + globals.c

**Step 1: Convert all struct definitions to extern declarations**
- Edit each `structs/*_struct.h`
- Change from: `struct { ... } name_;`
- Change to: `extern struct { ... } name_;`
- Result: Headers declare, don't define

**Step 2: Create `src/dophot_globals.c`**
- Define ALL 44 global variables exactly once
- Include all `structs/*_struct.h` headers
- This file compiled once, linked to everything
- ~400-500 lines

**Step 3: Update Makefile**
- Add `src/dophot_globals.o` to object list
- Link as FIRST object (ensures globals initialized first)
- Verify linker sees no duplicate definitions

**Step 4: Create context structure for reentrant API**
```c
typedef struct {
    // All the global state fields
    struct { float gxwid, gywid, skyguess; } tune1;
    struct { ... } tune2;
    // ... all 44 globals
    FILE *logfile;
} dophot_context_t;
```

### Phase 2: Reentrant API (optional, post-library-creation)
- Create `dophot_context_create()` / `dophot_context_destroy()`
- Modify functions to accept `dophot_context_t *ctx` parameter
- Allows multiple independent runs (true library behavior)
- Can be done after initial refactoring

---

## Implementation Plan

### Week 1: Conversion to extern + globals.c

**Task 1: Auto-convert struct headers** (~1 hour)
```bash
for file in structs/*_struct.h; do
    sed -i 's/^struct{/extern struct{/g' "$file"
done
```

**Task 2: Create globals.c** (~2 hours)
- Template: Include all 44 struct headers
- Define each one
- Result: ~450 lines

**Task 3: Update Makefile** (~1 hour)
- Add globals.o as first object
- Verify compilation

**Task 4: Test compilation** (~1 hour)
- Run `make clean && make`
- Verify NO linker errors
- Result: Working executable

**Task 5: Reference executable** (~1 hour)
- Create `bin/dophot.c` wrapper
- Link against library
- Test it works

### Timeline
- **Hours 1-3**: Struct header conversion + globals.c creation
- **Hours 4-5**: Makefile updates + initial testing
- **Hours 6-7**: Reference executable + full compilation test

---

## Success Criteria

✓ No linker errors about duplicate symbols  
✓ Executable builds without warnings  
✓ Reference `bin/dophot` works on test data  
✓ All 44 globals defined exactly once  
✓ Code ready for Phase 1b (exploration)

---

## Related Work

- Earlier session converted `/home/chris/projects/astro/DoPHOT_C/` the same way
- This version (Sahas_CDoPhot) has never been refactored
- Same fixes apply, but we'll use the newest version

---

## Next Steps

1. Create sed script to convert struct headers
2. Generate dophot_globals.c template
3. Run conversion on Sahas_CDoPhot version
4. Test compilation
5. Proceed to Phase 1b (exploration)
