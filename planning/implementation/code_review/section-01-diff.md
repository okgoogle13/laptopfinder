diff --git a/prompts/comet_discovery_agent.txt b/prompts/comet_discovery_agent.txt
index 5de9508..a0c2f59 100644
--- a/prompts/comet_discovery_agent.txt
+++ b/prompts/comet_discovery_agent.txt
@@ -30,7 +30,7 @@ Target Hardware & Keywords:
 - B200
 <!-- END_INJECT:TARGETS -->
 - Support colloquialisms and variants: "4090 lappy", "M1 Max 64GB", "Oculink", "Thunderbolt 5", "OLED digitizer".
-- UMA platforms: Apple Silicon Max/Ultra (64GB+ unified RAM) or AMD Strix Halo / Ryzen AI Max (64GB+).
+- UMA platforms: Apple Silicon Max/Ultra or AMD Strix Halo / Ryzen AI Max — minimum <!-- BEGIN_INJECT:UMA_MIN_RAM_GB -->32<!-- END_INJECT:UMA_MIN_RAM_GB --> GB unified/system RAM.
 
 AU Marketplace Search Heuristics (eBay AU primary):
 Use these Boolean strings as discovery seeds when scanning or querying marketplace text. Verify VRAM vs system RAM manually on any hit — marketplace algorithms conflate "16GB RAM" (system) with "16GB VRAM".
diff --git a/tests/test_prompt_markers.py b/tests/test_prompt_markers.py
index 5ebc089..ad95f24 100644
--- a/tests/test_prompt_markers.py
+++ b/tests/test_prompt_markers.py
@@ -4,7 +4,7 @@ from pathlib import Path
 def test_prompt_files_have_sentinel_markers():
     prompt_dir = Path(__file__).parent.parent / "prompts"
     expected = {
-        "comet_discovery_agent.txt": ["TARGETS"],
+        "comet_discovery_agent.txt": ["TARGETS", "UMA_MIN_RAM_GB"],
         "alternative_silicon_gemini.txt": ["UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"],
         "alternative_silicon_perplexity.txt": ["UMA_MIN_RAM_GB", "UMA_CHIP_PATTERNS", "TARGET_GPU_LIST"],
     }
