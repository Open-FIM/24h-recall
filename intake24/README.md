# Intake24 food mapping notes

This folder contains public-safe mapping support files for adapting Intake24 workflows to US dietary recall use cases.

## Included mapping file

`mappings/us_uk_category_map_suggestions.csv`

This file provides a reviewed mapping between US WWEIA/FNDDS food categories and Intake24-style food category codes/names.

Columns:

- `us_category_num`: US WWEIA/FNDDS category number
- `us_category_desc`: US WWEIA/FNDDS category description
- `uk_category_code`: matched Intake24/UK-style category code
- `uk_category_name`: matched Intake24/UK-style category name
- `score`: similarity score used during mapping review

## Intended use

This mapping was developed and reviewed to support US food entries in Intake24.

For most standard foods, the category mapping should support appropriate food grouping and image selection in Intake24. It is intended to help Intake24 display a reasonable matching image/category when US foods are imported or linked to Intake24 categories.

## Important limitation

This category-level mapping should work for most common foods, but it may not be sufficient for highly customized combination foods.

For customized mixed dishes, multi-component foods, or study-specific food combinations, list the individual items one by one whenever possible. This improves accuracy for:

- food identification
- portion estimation
- image matching
- nutrient calculation
- downstream food-level review

Examples where individual listing may be better than one combined entry:

- burrito with customized fillings
- salad with multiple toppings and dressing
- homemade casserole
- mixed rice or noodle dish
- sandwich with several added ingredients
- smoothie with multiple ingredients

## Not included

This repository does not include:

- full Intake24 food database dumps
- full USDA/FNDDS source data files
- image asset folders
- participant recall exports
- study-specific mapping overlays

The full Intake24 food/image/nutrient setup depends on the local Intake24 installation. This mapping file supports that setup, but it does not replace the Intake24 food database or image assets.
