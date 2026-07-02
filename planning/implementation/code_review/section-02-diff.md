diff --git a/src/laptopfinder/decide.py b/src/laptopfinder/decide.py
index dcb53dd..9d0d468 100644
--- a/src/laptopfinder/decide.py
+++ b/src/laptopfinder/decide.py
@@ -322,6 +322,27 @@ def _apply_architecture_penalty(gpu: str | None, tier: str | None, ref: dict) ->
     return 0
 
 
+def _apply_egpu_interconnect_penalty(analysis: dict, ref: dict) -> int:
+    """Return TB3/4 interconnect penalty for eGPU bundles; 0 otherwise.
+
+    Interconnect type is inferred from egpu_model keywords (no schema field exists).
+    zero_penalty_condition: system_ram_gb >= 32 waives penalty regardless of interconnect.
+    """
+    extracted = analysis.get("extracted_data", {})
+    model = extracted.get("exact_model_name")
+    egpu_model = extracted.get("egpu_model")
+    if not _has_egpu_bundle(model, egpu_model, ref):
+        return 0
+    system_ram = extracted.get("total_system_ram")
+    if system_ram and system_ram >= 32:
+        return 0
+    cfg = ref.get("egpu_interconnect_penalty", {})
+    egpu_lower = (egpu_model or "").lower()
+    if "oculink" in egpu_lower or "thunderbolt 5" in egpu_lower or "tb5" in egpu_lower:
+        return cfg.get("oculink_pts", 0)
+    return cfg.get("thunderbolt_3_4_pts", -3)
+
+
 def calculate_llm_index_score(
     analysis: dict,
     tier: str | None,
@@ -356,6 +377,7 @@ def calculate_llm_index_score(
             raw += 3
 
     raw += _apply_architecture_penalty(gpu, tier, ref)
+    raw += _apply_egpu_interconnect_penalty(analysis, ref)
 
     return max(0, min(100, raw))
 
diff --git a/tests/test_decide.py b/tests/test_decide.py
index 16278ae..c9aee53 100644
--- a/tests/test_decide.py
+++ b/tests/test_decide.py
@@ -23,6 +23,7 @@ from laptopfinder.decide import (
     _seller_reward_points,
     _deduction_points,
     _apply_architecture_penalty,
+    _apply_egpu_interconnect_penalty,
     calculate_llm_index_score,
 )
 
@@ -745,3 +746,54 @@ class TestSrlStorageFloors:
 
     def test_storage_floors_recommended_gb(self):
         assert load_ref()["storage_floors"]["recommended_gb"] == 1024
+
+
+class TestApplyEgpuInterconnectPenalty:
+    def _make_analysis(self, egpu_model=None, exact_model_name=None, system_ram=None):
+        return {
+            "extracted_data": {
+                "exact_model_name": exact_model_name,
+                "egpu_model": egpu_model,
+                "total_system_ram": system_ram,
+            }
+        }
+
+    def test_non_egpu_returns_zero(self):
+        analysis = self._make_analysis(exact_model_name="Dell XPS 15", egpu_model=None)
+        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0
+
+    def test_egpu_tb34_returns_penalty(self):
+        analysis = self._make_analysis(
+            exact_model_name="ASUS ROG Flow X13", egpu_model="Razer Core X", system_ram=16
+        )
+        assert _apply_egpu_interconnect_penalty(analysis, REF) == -3
+
+    def test_egpu_oculink_returns_zero(self):
+        analysis = self._make_analysis(
+            exact_model_name="ASUS ROG Flow X13", egpu_model="Minisforum DEG2 OCuLink"
+        )
+        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0
+
+    def test_egpu_thunderbolt5_returns_zero(self):
+        analysis = self._make_analysis(
+            exact_model_name="ASUS ROG Flow X13", egpu_model="Razer Core X Thunderbolt 5"
+        )
+        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0
+
+    def test_egpu_tb5_shorthand_returns_zero(self):
+        analysis = self._make_analysis(
+            exact_model_name="ASUS ROG Flow X13", egpu_model="Some Dock TB5"
+        )
+        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0
+
+    def test_zero_penalty_condition_system_ram_32(self):
+        analysis = self._make_analysis(
+            exact_model_name="ASUS ROG Flow X13", egpu_model="Razer Core X", system_ram=32
+        )
+        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0
+
+    def test_zero_penalty_condition_system_ram_64(self):
+        analysis = self._make_analysis(
+            exact_model_name="ASUS ROG Flow X13", egpu_model="Razer Core X", system_ram=64
+        )
+        assert _apply_egpu_interconnect_penalty(analysis, REF) == 0
