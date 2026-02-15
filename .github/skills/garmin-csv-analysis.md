# Skill: Garmin CSV Analysis

## Overview

Parse and normalize Garmin Connect CSV exports. The CSV parsing skill provides rules for handling manually downloaded Garmin CSV files.

## Expected CSV Formats

### Activities CSV (from Garmin Connect → Activities → Export)

| Column        | Type   | Notes                                                         |
| ------------- | ------ | ------------------------------------------------------------- |
| Activity Type | string | e.g., "Running", "Cycling", "Swimming"                        |
| Date          | string | Format varies: `YYYY-MM-DD HH:MM:SS` or `MM/DD/YYYY HH:MM:SS` |
| Favorite      | bool   | Ignore                                                        |
| Title         | string | User-defined activity name                                    |
| Distance      | float  | Kilometers (may use commas in some locales)                   |
| Calories      | int    | Total calories burned                                         |
| Time          | string | Duration as `H:MM:SS` or `MM:SS`                              |
| Avg HR        | int    | Average heart rate (may be empty)                             |
| Max HR        | int    | Maximum heart rate (may be empty)                             |

### Edge Cases to Handle

- **Locale differences**: European exports may use commas for decimals (`5,12` instead of `5.12`)
- **Empty fields**: HR, distance, and calories may be blank for some activity types (yoga, strength)
- **Date format variation**: Garmin uses different date formats depending on user locale
- **UTF-8 BOM**: Some CSV exports start with a BOM character — strip it
- **Header variations**: Column names may differ slightly between Garmin export versions

## Normalization Rules

1. **Distance**: Always convert to meters (input is usually km)
2. **Duration**: Always convert to seconds
3. **Activity type**: Map unknown types to `OTHER`
4. **Heart rate**: Keep as integers, `None` for missing values
5. **Dates**: Parse to `datetime` objects, never store as strings

## Testing

- Every new CSV column or format variation should have a test
- Use the `sample_activity_csv` fixture in `conftest.py` for standard test data
- Add edge case fixtures as discovered
