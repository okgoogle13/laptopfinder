# Code Review Interview — section-02-egpu-interconnect-penalty

## Findings and Dispositions

### HIGH: TB5 returns oculink_pts instead of thunderbolt_5_pts
**Disposition: AUTO-FIX**
Split OCuLink and TB5 into separate branches:
- OCuLink keyword OR known OCuLink enclosure → cfg.get("oculink_pts", 0)
- TB5 keyword → cfg.get("thunderbolt_5_pts", 0)
- Default → cfg.get("thunderbolt_3_4_pts", -3)

### HIGH: Minisforum DEG2 (OCuLink) penalized as TB3/4
**Disposition: AUTO-FIX**
Added `oculink_enclosures: ["Minisforum DEG2"]` to SRL `egpu_interconnect_penalty` block.
The function checks this list in addition to the "oculink" keyword. Test updated from
"Minisforum DEG2 OCuLink" (unrealistic) to bare "Minisforum DEG2" (canonical name).
Added separate "Generic OCuLink Dock" test for the keyword path.

### MEDIUM: Truthiness check on numeric field
**Disposition: AUTO-FIX**
Changed `if system_ram and system_ram >= 32:` → `if system_ram is not None and system_ram >= 32:`

### Undocumented path: egpu_model=None + enclosure in model_name
**Disposition: TEST ADDED, behavior documented**
`exact_model_name="ASUS ROG XG Mobile bundle", egpu_model=None` → has_egpu_bundle True,
egpu_lower="", no keywords match → returns -3 (conservative TB3/4 default).
Added test to document this as intentional. No code change; added comment to section doc.
