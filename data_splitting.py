import pandas as pd
from sklearn.model_selection import train_test_split

# ---- settings ----
INPUT_PATH = "SleepData.csv"
RANDOM_SEED = 42
SHUFFLE = True

# ---- load ----
df = pd.read_csv(INPUT_PATH)

# ---- split: 70% train, 30% temp ----
train_df, temp_df = train_test_split(
    df,
    test_size=0.30,
    random_state=RANDOM_SEED,
    shuffle=SHUFFLE
)

# ---- split temp into: 20% test, 10% val (i.e., 2/3 and 1/3 of the 30%) ----
val_df, test_df = train_test_split(
    temp_df,
    test_size=(2/3),          # makes test = 20% of full, val = 10% of full
    random_state=RANDOM_SEED,
    shuffle=SHUFFLE
)

# ---- sanity check ----
n = len(df)
print("Total:", n)
print("Train:", len(train_df), f"({len(train_df)/n:.1%})")
print("Test :", len(test_df),  f"({len(test_df)/n:.1%})")
print("Val  :", len(val_df),   f"({len(val_df)/n:.1%})")

# ---- save ----
train_df.to_csv("SleepData_train.csv", index=False)
test_df.to_csv("SleepData_test.csv", index=False)
val_df.to_csv("SleepData_val.csv", index=False)
