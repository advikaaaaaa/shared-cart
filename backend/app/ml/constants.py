"""Constants copied from CapstoneProject.ipynb. Do not treat these as empirically optimal."""

SEED = 42
GRID = 10
CELL_METRES = 300
THRESHOLD = 149
FEE = 40.0
MAXW = 15
WARMUP_DAYS = 7
TOTAL_DAYS = 65
TRAIN_LAST_DAY = 48
ORDERS_PER_DAY = 1200
OPEN_HOUR, CLOSE_HOUR = 7, 23
N_USERS = 4000
WAITS = [2, 5, 8, 10, 15]
RADII = {300: 0, 600: 1, 900: 2}
RADIUS_LIST = [300, 600, 900]
DETOUR_MIN = 2.0
LAM = 2.0
PEAK_HOURS = (12, 13, 19, 20, 21)
WAIT_X_CELLS = {300: 1, 600: 9, 900: 25}

ORIGINAL_FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "is_peak_hour",
    "grid_row",
    "grid_col",
    "zone_type",
    "order_value",
    "n_items",
    "orders_in_cell_last_15min",
    "avg_orders_in_cell_this_hour",
    "user_past_order_count",
    "user_small_order_ratio",
    "small_orders_300m_last_15min",
    "small_orders_600m_last_15min",
    "small_orders_900m_last_15min",
    "wait_minutes",
    "radius_m",
]

FINAL_FEATURES = [
    "hour",
    "day_of_week",
    "is_peak_hour",
    "grid_row",
    "grid_col",
    "order_value",
    "n_items",
    "orders_in_cell_last_15min",
    "avg_orders_in_cell_this_hour",
    "user_past_order_count",
    "user_small_order_ratio",
    "small_orders_600m_last_15min",
    "small_orders_900m_last_15min",
    "wait_minutes",
    "radius_m",
    "hour_sin",
    "hour_cos",
    "recent_in_chosen_radius",
    "expected_arrivals",
    "busy_ratio",
    "wait_x_cells",
    "is_dense_zone",
    "zone_type",
]

ZONE_LABELS = {
    "commercial": "Commercial",
    "dense_residential": "Dense residential",
    "normal_residential": "Residential",
    "quiet": "Quiet",
}
