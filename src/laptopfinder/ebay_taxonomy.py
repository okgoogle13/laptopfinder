def ebay_category_id(ref: dict) -> str:
    """Return the eBay leaf category ID for laptop searches from the SRL."""
    return ref.get("ebay_aspect_filter", {}).get("category_id", "175672")


def build_aspect_filter(ref: dict) -> str | None:
    """Build the eBay Browse API aspect_filter string for GPU memory size.

    Returns None when no gpu_memory_size_values are configured, so callers
    can cleanly skip adding the param rather than sending an empty string.
    """
    cfg = ref.get("ebay_aspect_filter", {})
    values = cfg.get("gpu_memory_size_values", [])
    if not values:
        return None
    cat_id = ebay_category_id(ref)
    encoded = "|".join(values)
    return f"categoryId:{cat_id},GPU Memory Size:{{{encoded}}}"
