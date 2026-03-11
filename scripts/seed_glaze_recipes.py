"""
Seed glaze recipes for the New Collection.
Data extracted from the Google Spreadsheet "Расчет рецептов" → "new collection" tab.

Stores:
  - Material records for each glaze ingredient (per factory, idempotent)
  - Recipe records for each glaze color
  - RecipeMaterial records linking recipes to ingredients (ratio as quantity_per_unit)

Usage:
    DATABASE_URL=<url> python scripts/seed_glaze_recipes.py
    # or just: python scripts/seed_glaze_recipes.py  (uses .env DATABASE_URL)

Notes:
  - Idempotent: safe to run multiple times; existing records are skipped.
  - quantity_per_unit stores the ingredient's fraction of the total dry batch (e.g. 0.2 for 20%).
  - unit = "fraction"  →  grams_needed = fraction × desired_batch_grams
  - recipe.description contains batch metadata as JSON:
      reference_batch_g, water_fraction, water_ml_per_2boards,
      coverage_note, special_kiln (Lagoon Spark only).
"""

import sys
import os
import json
import uuid
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from api.database import SessionLocal
from api.models import Factory, Material, Recipe, RecipeMaterial

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("seed_glaze")

# ─────────────────────────────────────────────────────────────
# Raw data from spreadsheet "new collection" tab
# Each ingredient: (name, fraction_of_dry_batch)
# reference_batch_g  → reference batch dry weight (g)
# water_fraction     → water weight as fraction of dry batch
# water_ml_per_2boards → water volume annotation from spreadsheet header
# coverage_note      → extra coverage / kiln note from spreadsheet
# ─────────────────────────────────────────────────────────────
GLAZE_RECIPES = [
    {
        "name": "Wabi Beige",
        "collection": "new_collection",
        "reference_batch_g": 500,
        "water_fraction": 0.6,
        "water_ml_per_2boards": 450,
        "coverage_note": "450ml/2papan",
        "special_kiln": None,
        "ingredients": [
            ("Fritt Tomat",    0.2),
            ("Fritt Kasm",     0.8),
            ("Black pigment",  0.0004),
            ("Yellow pigment", 0.0015),
            ("Golden brown",   0.0012),
            ("Bentonite",      0.01),
        ],
    },
    {
        "name": "Frosted White",
        "collection": "new_collection",
        "reference_batch_g": 200,
        "water_fraction": 0.6,
        "water_ml_per_2boards": 450,
        "coverage_note": "450ml/2papan",
        "special_kiln": None,
        "ingredients": [
            ("Fritt Tomat", 0.2),
            ("Fritt Kasm",  0.8),
            ("Bentonite",   0.01),
        ],
    },
    {
        "name": "Matcha Leaf",
        "collection": "new_collection",
        "reference_batch_g": 11000,
        "water_fraction": 0.6,
        "water_ml_per_2boards": 450,
        "coverage_note": "450ml/2papan; large batch for pigment precision",
        "special_kiln": None,
        "ingredients": [
            ("Fritt Tomat",    0.2),
            ("Fritt Kasm",     0.8),
            ("Green 9444",     0.008),
            ("Yellow 9433",    0.03),
            ("Bentonite",      0.01),
        ],
    },
    {
        "name": "Frost Blue",
        "collection": "new_collection",
        "reference_batch_g": 300,
        "water_fraction": 0.6,
        "water_ml_per_2boards": 450,
        "coverage_note": "450ml/2papan",
        "special_kiln": None,
        "ingredients": [
            ("Fritt Tomat",    0.2),
            ("Fritt Kasm",     0.8),
            ("Turquoise 9411", 0.005),
            ("Bentonite",      0.01),
        ],
    },
    {
        "name": "Lavender Ash",
        "collection": "new_collection",
        "reference_batch_g": 200,
        "water_fraction": 0.6,
        "water_ml_per_2boards": 450,
        "coverage_note": "450ml/2papan",
        "special_kiln": None,
        "ingredients": [
            ("Fritt Tomat",    0.2),
            ("Fritt Kasm",     0.8),
            ("Grey pigment",   0.012),
            ("Violet 9474",    0.027),
            ("Bentonite",      0.01),
        ],
    },
    {
        "name": "Mocha Mousse",
        "collection": "new_collection",
        "reference_batch_g": 200,
        "water_fraction": 0.6,
        "water_ml_per_2boards": 450,
        "coverage_note": "450ml/2papan",
        "special_kiln": None,
        "ingredients": [
            ("Fritt Tomat",    0.2),
            ("Fritt Kasm",     0.8),
            ("Golden brown",   0.008),
            ("Violet 9474",    0.018),
            ("Bentonite",      0.01),
        ],
    },
    {
        "name": "Wild Olive",
        "collection": "new_collection",
        "reference_batch_g": 200,
        "water_fraction": 0.6,
        "water_ml_per_2boards": None,
        "coverage_note": None,
        "special_kiln": None,
        "ingredients": [
            ("Fritt Tomat",   0.2),
            ("Fritt Kasm",    0.8),
            ("Green pigment", 0.02),
            ("Golden brown",  0.03),
            ("Bentonite",     0.01),
        ],
    },
    {
        "name": "Milk Crackle",
        "collection": "new_collection",
        "reference_batch_g": 500,
        "water_fraction": 0.6,
        "water_ml_per_2boards": None,
        "coverage_note": None,
        "special_kiln": None,
        "ingredients": [
            ("Fritt Tomat",   0.2),
            ("Fritt Kasm",    0.8),
            ("Zircosil",      0.1),
            ("Golden brown",  0.0015),
        ],
    },
    {
        "name": "Jade Mist",
        "collection": "new_collection",
        "reference_batch_g": 800,
        "water_fraction": 0.6,
        "water_ml_per_2boards": None,
        "coverage_note": None,
        "special_kiln": None,
        "ingredients": [
            ("Fritt Tomat",       0.2),
            ("Fritt Kasm",        0.8),
            ("Copper carbonate",  0.016),
            ("Iron oxide",        0.05),
            ("Bentonite",         0.01),
        ],
    },
    {
        "name": "Lagoon Spark",
        "collection": "new_collection",
        "reference_batch_g": 6000,
        "water_fraction": 0.7,
        "water_ml_per_2boards": 500,
        "coverage_note": "500ml/2papan",
        "special_kiln": "New kiln 1012°C – 5 min hold",
        "ingredients": [
            ("Fritt Tomat",      0.9),
            ("Kaolin",           0.1),
            ("Copper carbonate", 0.05),
            ("Sodium silicate",  0.006),
            ("CMC",              0.0015),
        ],
    },
    {
        "name": "Rose Dust",
        "collection": "new_collection",
        "reference_batch_g": 400,
        "water_fraction": 0.6,
        "water_ml_per_2boards": None,
        "coverage_note": None,
        "special_kiln": None,
        "ingredients": [
            ("Fritt Tomat",  0.2),
            ("Fritt Kasm",   0.8),
            ("Coral pigment", 0.004),
            ("Violet",       0.0024),
            ("Bentonite",    0.01),
        ],
    },
    {
        "name": "Wild Honey",
        "collection": "new_collection",
        "reference_batch_g": 100,
        "water_fraction": 0.6,
        "water_ml_per_2boards": None,
        "coverage_note": None,
        "special_kiln": None,
        "ingredients": [
            ("Fritt Tomat",    0.2),
            ("Fritt Kasm",     0.8),
            ("Orange pigment", 0.005),
            ("Yellow pigment", 0.045),
            ("Bentonite",      0.01),
        ],
    },
]

# All unique ingredient material names
ALL_INGREDIENTS = sorted({
    ing[0]
    for recipe in GLAZE_RECIPES
    for ing in recipe["ingredients"]
})


def get_or_create_material(db, name: str, factory_id) -> "Material":
    """Get existing material by name+factory or create it."""
    mat = (
        db.query(Material)
        .filter(Material.name == name, Material.factory_id == factory_id)
        .first()
    )
    if mat:
        return mat
    mat = Material(
        id=uuid.uuid4(),
        name=name,
        factory_id=factory_id,
        balance=0,
        min_balance=0,
        unit="kg",
        material_type="glaze_ingredient",
        warehouse_section="raw_materials",
    )
    db.add(mat)
    db.flush()
    log.info("  Created material: %s (factory %s)", name, factory_id)
    return mat


def get_or_create_recipe(db, name: str, data: dict) -> "Recipe":
    """Get existing recipe by name or create it."""
    recipe = db.query(Recipe).filter(Recipe.name == name).first()
    if recipe:
        return recipe

    description = json.dumps({
        "reference_batch_g": data["reference_batch_g"],
        "water_fraction": data["water_fraction"],
        "water_ml_per_2boards": data["water_ml_per_2boards"],
        "coverage_note": data["coverage_note"],
        "special_kiln": data["special_kiln"],
        "source": "new_collection spreadsheet",
    }, ensure_ascii=False)

    recipe = Recipe(
        id=uuid.uuid4(),
        name=name,
        collection=data["collection"],
        color=name,
        description=description,
        is_active=True,
    )
    db.add(recipe)
    db.flush()
    log.info("  Created recipe: %s", name)
    return recipe


def seed():
    db = SessionLocal()
    try:
        factories = db.query(Factory).all()
        if not factories:
            log.error("No factories found in database. Create factories first.")
            return

        log.info("Found %d factories: %s", len(factories),
                 ", ".join(f.name for f in factories))

        # ── 1. Ensure all glaze ingredient Materials exist per factory ──────
        log.info("\n── Creating glaze ingredient materials ──")
        # materials[factory_id][ingredient_name] = Material
        materials: dict[str, dict[str, Material]] = {}
        for factory in factories:
            fid = str(factory.id)
            materials[fid] = {}
            for ing_name in ALL_INGREDIENTS:
                mat = get_or_create_material(db, ing_name, factory.id)
                materials[fid][ing_name] = mat

        db.flush()

        # ── 2. Create Recipe + RecipeMaterial records ────────────────────────
        log.info("\n── Creating recipes ──")
        created_recipes = 0
        skipped_recipes = 0
        created_rm = 0
        skipped_rm = 0

        for recipe_data in GLAZE_RECIPES:
            recipe = get_or_create_recipe(db, recipe_data["name"], recipe_data)
            if db.query(Recipe).filter(Recipe.id == recipe.id).count() == 0:
                created_recipes += 1
            else:
                skipped_recipes += 1

            # Add Water as a special ingredient (its fraction stored in recipe metadata)
            # but also as a RecipeMaterial so material consumption can be tracked
            all_ings = list(recipe_data["ingredients"])
            # Append water
            all_ings.append(("Water", recipe_data["water_fraction"]))

            for factory in factories:
                fid = str(factory.id)
                for ing_name, fraction in all_ings:
                    # Ensure water material exists for this factory
                    if ing_name not in materials[fid]:
                        mat = get_or_create_material(db, ing_name, factory.id)
                        materials[fid][ing_name] = mat
                    mat = materials[fid][ing_name]

                    existing_rm = (
                        db.query(RecipeMaterial)
                        .filter(
                            RecipeMaterial.recipe_id == recipe.id,
                            RecipeMaterial.material_id == mat.id,
                        )
                        .first()
                    )
                    if existing_rm:
                        skipped_rm += 1
                        continue

                    grams_in_ref = round(fraction * recipe_data["reference_batch_g"], 4)
                    rm = RecipeMaterial(
                        id=uuid.uuid4(),
                        recipe_id=recipe.id,
                        material_id=mat.id,
                        quantity_per_unit=fraction,
                        unit="fraction",
                        notes=(
                            f"{grams_in_ref}g per {recipe_data['reference_batch_g']}g "
                            f"reference batch | factory: {factory.name}"
                        ),
                    )
                    db.add(rm)
                    created_rm += 1

        db.commit()

        log.info("\n✓ Done.")
        log.info("  Recipes created: %d  skipped: %d", created_recipes, skipped_recipes)
        log.info("  RecipeMaterials created: %d  skipped: %d", created_rm, skipped_rm)
        log.info("  Total glaze recipes: %d", len(GLAZE_RECIPES))
        log.info("  Total unique ingredients: %d", len(ALL_INGREDIENTS) + 1)  # +1 for water

    except Exception as e:
        db.rollback()
        log.exception("Seeding failed: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
