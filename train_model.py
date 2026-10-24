import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import pickle
import os
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (roc_auc_score, average_precision_score,
                             classification_report)

# ── 0. 加载数据 ──────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
daily_df   = pd.read_csv(os.path.join(BASE_DIR, "daily_records.csv"),
                         parse_dates=["date"])
daily_df   = daily_df.sort_values(["player_id", "date"]).reset_index(drop=True)

# ── 1. 补缺失特征 ─────────────────────────────────────────────

# days_since_last_match（生成时没算，这里补上）
daily_df["is_match"] = (daily_df["day_type"] == "match").astype(int)
def days_since_match(series):
    result = []
    count  = 999
    for v in series:
        if v == 1:
            count = 0
        else:
            count += 1
        result.append(count)
    return result

daily_df["days_since_last_match"] = (
    daily_df.groupby("player_id")["is_match"]
    .transform(lambda x: days_since_match(x.tolist()))
)

# position → One-Hot
daily_df = pd.get_dummies(daily_df, columns=["position"], prefix="pos")

# ── 2. 数据清洗 ───────────────────────────────────────────────

# 去掉需要排除的行（受伤期间 + 赛季末7天）
df_clean = daily_df[~daily_df["exclude_from_training"]].copy()

# 去掉休息日（无负荷数据，不是预测场景）
df_clean = df_clean[df_clean["day_type"] != "rest"].copy()

# 去掉 acwr 为空的行（赛季最初28天内慢性负荷不稳定）
df_clean = df_clean.dropna(subset=["acwr", "load_change_pct"])

print(f"清洗后样本数: {len(df_clean)}")
print(f"正样本（将受伤）: {df_clean['injury_next_7d'].sum()}")
print(f"正样本比例: {df_clean['injury_next_7d'].mean():.2%}")

# ── 3. 选择特征 ───────────────────────────────────────────────
pos_cols = [c for c in df_clean.columns if c.startswith("pos_")]

FEATURES = [
    # 负荷核心
    "acwr", "load_7d", "load_28d", "load_change_pct",
    "individual_load_zscore",
    # 高强度跑
    "hsr_7d", "sprint_7d",
    # 恢复状态
    "fatigue_7d_mean", "soreness_7d_mean",
    "sleep_duration", "hrv_rmssd",
    # 比赛密度
    "matches_last_14d", "days_since_last_match",
    # 当日状态
    "session_rpe", "srpe_load",
    # 球员背景
    "age", "previous_injury_count", "days_since_last_injury",
] + pos_cols

# 只保留实际存在的列（防止某些列名对不上）
FEATURES = [f for f in FEATURES if f in df_clean.columns]

X = df_clean[FEATURES]
y = df_clean["injury_next_7d"]

print(f"\n特征数量: {len(FEATURES)}")
print("特征列表:", FEATURES)

# ── 4. 时序切分 + XGBoost训练 ─────────────────────────────────
# 关键：按时间排序切分，不能随机shuffle
df_clean = df_clean.reset_index(drop=True)
X = df_clean[FEATURES].replace([np.inf, -np.inf], np.nan)
X = X.fillna(X.median())
y = df_clean["injury_next_7d"]

# 处理类别不平衡
neg   = (y == 0).sum()
pos   = (y == 1).sum()
spw   = neg / pos
print(f"\nscale_pos_weight = {spw:.1f}  (负:{neg} / 正:{pos})")

tscv  = TimeSeriesSplit(n_splits=5)
auc_scores = []
pr_scores  = []

for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
    X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

    model = xgb.XGBClassifier(
        n_estimators        = 400,
        max_depth           = 5,
        learning_rate       = 0.05,
        subsample           = 0.8,
        colsample_bytree    = 0.8,
        min_child_weight    = 1,
        scale_pos_weight    = spw,
        eval_metric         = "aucpr",
        early_stopping_rounds = 30,
        random_state        = 42,
        verbosity           = 0,
    )
    model.fit(X_tr, y_tr,
              eval_set=[(X_val, y_val)],
              verbose=False)

    y_prob = model.predict_proba(X_val)[:, 1]
    auc    = roc_auc_score(y_val, y_prob)
    pr     = average_precision_score(y_val, y_prob)
    auc_scores.append(auc)
    pr_scores.append(pr)
    print(f"  Fold {fold+1}  AUC-ROC={auc:.3f}  PR-AUC={pr:.3f}")

valid_auc = [s for s in auc_scores if not np.isnan(s)]
print(f"平均 AUC-ROC : {np.mean(valid_auc):.3f} ± {np.std(valid_auc):.3f}  ({len(valid_auc)}/5 折有效)")
print(f"平均 PR-AUC  : {np.nanmean(pr_scores):.3f} ± {np.nanstd(pr_scores):.3f}")

# ── 5. 用全量数据训练最终模型 ──────────────────────────────────
final_model = xgb.XGBClassifier(
    n_estimators     = 400,
    max_depth        = 4,
    learning_rate    = 0.05,
    subsample        = 0.8,
    colsample_bytree = 0.8,
    scale_pos_weight = spw,
    random_state     = 42,
    verbosity        = 0,
)
final_model.fit(X, y)

# 保存模型
model_path = os.path.join(BASE_DIR, "injury_model.pkl")
with open(model_path, "wb") as f:
    pickle.dump({"model": final_model, "features": FEATURES}, f)
print(f"\n模型已保存 → {model_path}")

# ── 6. SHAP 解释（验证可解释性）──────────────────────────────
explainer   = shap.TreeExplainer(final_model)
shap_values = explainer.shap_values(X)

print("\n=== 全局特征重要性（SHAP均值）===")
shap_importance = pd.Series(
    np.abs(shap_values).mean(axis=0),
    index=FEATURES
).sort_values(ascending=False)
print(shap_importance.head(10))

# 保存SHAP解释器（Agent推理时用）
shap_path = os.path.join(BASE_DIR, "shap_explainer.pkl")
with open(shap_path, "wb") as f:
    pickle.dump(explainer, f)
print(f"SHAP解释器已保存 → {shap_path}")