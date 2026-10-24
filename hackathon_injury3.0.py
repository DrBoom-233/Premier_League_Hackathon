import numpy as np
import pandas as pd
from datetime import date, timedelta
import random
import os

np.random.seed(42)
random.seed(42)

# ─────────────────────────────────────────
# 1. 球员基础信息
# ─────────────────────────────────────────
POSITIONS = ["GK", "CB", "LB", "RB", "CM", "CAM", "LW", "RW", "ST"]
# 每90分钟的位置跑动基准（参考英超追踪数据）
POSITION_NORMS = {
    "GK":  {"total": 5800,  "hsr": 120,  "sprint": 60,   "accel": 10, "decel": 8,  "max_speed": 20},
    "CB":  {"total": 10500, "hsr": 600,  "sprint": 200,  "accel": 22, "decel": 20, "max_speed": 28},
    "LB":  {"total": 11500, "hsr": 1000, "sprint": 400,  "accel": 30, "decel": 28, "max_speed": 31},
    "RB":  {"total": 11500, "hsr": 1000, "sprint": 400,  "accel": 30, "decel": 28, "max_speed": 31},
    "CM":  {"total": 11200, "hsr": 700,  "sprint": 250,  "accel": 28, "decel": 26, "max_speed": 30},
    "CAM": {"total": 10800, "hsr": 850,  "sprint": 320,  "accel": 26, "decel": 24, "max_speed": 31},
    "LW":  {"total": 11000, "hsr": 1100, "sprint": 520,  "accel": 32, "decel": 28, "max_speed": 33},
    "RW":  {"total": 11000, "hsr": 1100, "sprint": 520,  "accel": 32, "decel": 28, "max_speed": 33},
    "ST":  {"total": 10000, "hsr": 950,  "sprint": 480,  "accel": 28, "decel": 25, "max_speed": 32},
}

def generate_squad(n_players=25):
    players = []
    for i in range(1, n_players + 1):
        pos = random.choice(POSITIONS)
        players.append({
            "player_id":        f"P{i:03d}",
            "age":              np.random.randint(18, 36),
            "position":         pos,
            # 体能基线（影响正常负荷水平）
            "base_fitness":     np.random.uniform(0.6, 1.0),
            # 历史伤病倾向（隐变量，用于驱动伤病概率）
            "injury_prone":     np.random.beta(2, 5),
        })
    return pd.DataFrame(players)

# ─────────────────────────────────────────
# 2. 赛季日历（38轮联赛 + 训练日）
# ─────────────────────────────────────────
def build_season_calendar(start: date, n_weeks: int = 40):
    """
    每周模式：周二训练、周三训练/休息、周四训练、
              周五训练、周六/周日比赛、周一休息
    """
    calendar = []
    d = start
    for _ in range(n_weeks * 7):
        dow = d.weekday()   # 0=Mon … 6=Sun
        if dow == 0:
            day_type = "rest"
        elif dow in [1, 3, 4]:
            day_type = "training"
        elif dow == 2:
            day_type = "training" if random.random() > 0.3 else "rest"
        else:  # 5=Sat, 6=Sun
            day_type = "match" if random.random() > 0.5 else "training"
        calendar.append({"date": d, "day_type": day_type})
        d += timedelta(days=1)
    return pd.DataFrame(calendar)

# ─────────────────────────────────────────
# 3. 每日负荷 & 恢复数据生成
# ─────────────────────────────────────────
def daily_workload(day_type: str, position: str, fitness: float,
                   participation: str = "starter"):
    """
    participation: "starter"(首发), "sub"(替补上场), "bench"(未上场), "bench_gk"(备用门将)
    """
    norms = POSITION_NORMS.get(position, POSITION_NORMS["CM"])

    # 未上场：休息，无负荷
    if day_type == "rest" or participation in ("bench", "bench_gk"):
        return dict(match_minutes=0, training_minutes=0,
                    total_distance=0, hsr_distance=0, sprint_distance=0,
                    acceleration_count=0, deceleration_count=0,
                    max_speed=0.0, session_rpe=0.0, srpe_load=0.0)

    if day_type == "match":
        mins = np.random.randint(60, 91) if participation == "starter" \
               else np.random.randint(15, 46)   # 替补上场时间
        scale = mins / 90.0
        rpe   = round(np.random.uniform(6.5, 9.5), 1)   # ← 只生成一次

        return dict(
            match_minutes=mins,
            training_minutes=0,
            total_distance   =max(0, round(np.random.normal(norms["total"]  * scale * fitness,
                                                             norms["total"]  * 0.08))),
            hsr_distance     =max(0, round(np.random.normal(norms["hsr"]    * scale,
                                                             norms["hsr"]    * 0.15))),
            sprint_distance  =max(0, round(np.random.normal(norms["sprint"] * scale,
                                                             norms["sprint"] * 0.20))),
            acceleration_count =max(0, int(np.random.normal(norms["accel"] * scale, 3))),
            deceleration_count =max(0, int(np.random.normal(norms["decel"] * scale, 3))),
            max_speed          =round(np.random.normal(norms["max_speed"], 1.5), 1),
            session_rpe        =rpe,
            srpe_load          =round(mins * rpe, 1),   # ← Fix: Duration × 同一个RPE
        )

    # training
    mins      = np.random.randint(60, 105)
    intensity = np.random.uniform(0.5, 1.0)
    rpe       = round(np.random.uniform(3, 8) * intensity, 1)   # ← 同样只生成一次

    return dict(
        match_minutes=0,
        training_minutes   =mins,
        total_distance     =max(0, round(np.random.normal(
                                norms["total"] * 0.6 * intensity * fitness,
                                norms["total"] * 0.06))),
        hsr_distance       =max(0, round(np.random.normal(
                                norms["hsr"] * 0.4 * intensity, norms["hsr"] * 0.15))),
        sprint_distance    =max(0, round(np.random.normal(
                                norms["sprint"] * 0.3 * intensity, norms["sprint"] * 0.2))),
        acceleration_count =max(0, int(np.random.normal(norms["accel"] * 0.5 * intensity, 3))),
        deceleration_count =max(0, int(np.random.normal(norms["decel"] * 0.5 * intensity, 3))),
        max_speed          =round(np.random.normal(norms["max_speed"] * 0.85, 1.5), 1),
        session_rpe        =rpe,
        srpe_load          =round(mins * rpe, 1),   # ← Fix
    )

def daily_wellness(day_type: str, fatigue_carry: float):
    """
    1 = 最好（完全恢复）  5 = 最差（极度疲劳）
    fatigue_carry 越高 → 各项wellness分数越高（越差）
    """
    # fatigue_carry 范围 0~1.5，映射到评分偏移 0~2
    fatigue_offset = fatigue_carry * 1.3

    fatigue_mean   = np.clip(2.0 + fatigue_offset, 1, 5)   # 正常2分，累了往5走
    soreness_base  = 3.5 if day_type == "match" else 2.5
    soreness_mean  = np.clip(soreness_base + fatigue_offset * 0.7, 1, 5)

    # 睡眠质量：累了反而睡不好（分数偏高=差）
    sleep_quality_mean = np.clip(2.5 + fatigue_offset * 0.5, 1, 5)

    return dict(
        sleep_duration  =round(np.clip(np.random.normal(7.2 - fatigue_carry * 0.5, 0.8), 4, 10), 1),
        sleep_quality   =int(np.clip(np.random.normal(sleep_quality_mean, 0.7), 1, 5)),
        fatigue_score   =int(np.clip(np.random.normal(fatigue_mean,  0.8), 1, 5)),
        muscle_soreness =int(np.clip(np.random.normal(soreness_mean, 0.9), 1, 5)),
        stress_level    =int(np.clip(np.random.normal(2.5 + fatigue_offset * 0.3, 0.8), 1, 5)),
        resting_hr      =round(np.clip(np.random.normal(58 + fatigue_carry * 6, 5), 42, 90)),
        hrv_rmssd       =round(np.clip(np.random.normal(65 - fatigue_carry * 10, 10), 20, 120), 1),
    )

# ─────────────────────────────────────────
# 4. 核心：伤病概率函数
# ─────────────────────────────────────────
def injury_probability(acwr, fatigue_7d, soreness_7d,
                        prev_injuries, days_since_injury,
                        day_type, injury_prone):
    """
    依据运动科学文献的伤病风险因子加权计算概率
    基础受伤率: 约每球员每赛季1.5次 ≈ 每场比赛0.010
    """
    if day_type not in ("match", "training"):
        return 0.0

    base = 0.010 if day_type == "match" else 0.003

    # ACWR乘数大幅加强（原来最高4倍，现在最高15倍）
    if   acwr is None or np.isnan(acwr): acwr_mult = 1.0
    elif acwr < 0.8:   acwr_mult = 1.5
    elif acwr <= 1.3:  acwr_mult = 1.0   # 安全区间
    elif acwr <= 1.5:  acwr_mult = 4.0   # 原来1.5
    elif acwr <= 2.0:  acwr_mult = 10.0  # 原来2.5
    else:              acwr_mult = 18.0  # 原来4.0

    # 疲劳效果加强（原来系数0.3，现在0.9）
    fatigue_mult  = max(0.3, 1 + (fatigue_7d  - 3) * 0.9)
    soreness_mult = max(0.3, 1 + (soreness_7d - 3) * 0.6)

    history_mult  = 1 + min(prev_injuries, 5) * 0.3
    recency_mult  = 2.5 if days_since_injury < 30 else 1.0

    p = base * acwr_mult * fatigue_mult * soreness_mult * \
        history_mult * recency_mult * (1 + injury_prone * 2)

    return min(p, 0.25)

# ─────────────────────────────────────────
# 5. 主生成函数
# ─────────────────────────────────────────
# 删掉原来的 INJURY_TYPES / BODY_LOCATIONS / MECHANISMS
# 换成：
INJURY_PROFILES = [
    # type          locations                               Non-contact/Contact/Unknown
    ("Hamstring", ["Left Hamstring", "Right Hamstring"],   [0.85, 0.10, 0.05]),
    ("Calf",      ["Left Calf",      "Right Calf"],        [0.80, 0.15, 0.05]),
    ("Quad",      ["Left Quad",      "Right Quad"],        [0.70, 0.20, 0.10]),
    ("Groin",     ["Groin"],                               [0.75, 0.15, 0.10]),
    ("Back",      ["Lower Back",     "Upper Back"],        [0.60, 0.30, 0.10]),
    ("Ankle",     ["Left Ankle",     "Right Ankle"],       [0.30, 0.60, 0.10]),
    ("Knee",      ["Left Knee",      "Right Knee"],        [0.45, 0.45, 0.10]),
]
MECHANISMS = ["Non-contact", "Contact", "Unknown"]

def generate_season(n_players=25, n_weeks=40,
                    start_date=date(2025, 8, 1)):
    players   = generate_squad(n_players)
    calendar  = build_season_calendar(start_date, n_weeks)

    all_daily    = []
    all_injuries = []

    def select_match_lineup(players_df):
        """返回每个player_id当天的出场状态"""
        gks      = players_df[players_df["position"] == "GK"]["player_id"].tolist()
        outfield = players_df[players_df["position"] != "GK"]["player_id"].tolist()

        starting_gk   = random.sample(gks, 1) if gks else []
        bench_gks     = [p for p in gks if p not in starting_gk]

        n_out_start   = min(10, len(outfield))
        starters_out  = random.sample(outfield, n_out_start)
        bench_out     = [p for p in outfield if p not in starters_out]

        n_subs        = min(random.randint(3, 5), len(bench_out))
        subs          = random.sample(bench_out, n_subs)
        bench_no_play = [p for p in bench_out if p not in subs]

        result = {}
        for pid in starting_gk + starters_out:
            result[pid] = "starter"
        for pid in subs:
            result[pid] = "sub"
        for pid in bench_gks:
            result[pid] = "bench_gk"
        for pid in bench_no_play:
            result[pid] = "bench"
        return result
    
    # generate_season 函数内，players 和 calendar 生成之后加这段
    match_lineups = {}   # date -> {player_id: participation}
    for _, day in calendar[calendar["day_type"] == "match"].iterrows():
        match_lineups[day["date"]] = select_match_lineup(players)


    for _, player in players.iterrows():
        pid = player["player_id"]

        # 球员状态跟踪
        injury_history_count = 0
        last_injury_date     = None
        is_injured           = False
        injury_return_date   = None
        fatigue_carry        = 0.0    # 跨天累积疲劳
        raw_rows             = []     # 先存原始数据，再算衍生特征

        for _, day in calendar.iterrows():
            d         = day["date"]
            day_type  = day["day_type"]

            # 如果受伤中 → 强制休息
            if is_injured:
                if d >= injury_return_date:
                    is_injured = False
                else:
                    day_type = "rest"

            participation = match_lineups.get(d, {}).get(pid, "bench") \
                if day_type == "match" else "starter"
            wl = daily_workload(day_type, player["position"], player["base_fitness"], participation)            
            wel = daily_wellness(day_type, fatigue_carry)

            # 更新疲劳状态（比赛后疲劳增加，休息后减少）
            if day_type == "match":
                fatigue_carry = min(fatigue_carry + 0.4, 1.5)
            elif day_type == "training":
                fatigue_carry = min(fatigue_carry + 0.1, 1.5)
            else:
                fatigue_carry = max(fatigue_carry - 0.25, 0.0)

            days_since_inj = (
                (d - last_injury_date).days if last_injury_date else 999
            )

            raw_rows.append({
                "player_id": pid,
                "date":      d,
                "day_type":  day_type,
                "is_injured_today": is_injured,
                "days_since_last_injury": days_since_inj,
                "previous_injury_count":  injury_history_count,
                **wl,
                **wel,
            })

           
            

        # ── 计算衍生特征（滚动窗口，必须用 pandas） ──
        df_p = pd.DataFrame(raw_rows)
        df_p = df_p.sort_values("date").reset_index(drop=True)

        df_p["load_7d"]   = df_p["srpe_load"].rolling(7,  min_periods=1).sum()
        df_p["load_28d"]  = df_p["srpe_load"].rolling(28, min_periods=7).sum()
        df_p["hsr_7d"]    = df_p["hsr_distance"].rolling(7, min_periods=1).sum()
        df_p["sprint_7d"] = df_p["sprint_distance"].rolling(7, min_periods=1).sum()

        chronic_avg       = df_p["load_28d"] / 4
        df_p["acwr"]      = (df_p["load_7d"] / chronic_avg.replace(0, np.nan)).round(3)
        df_p["load_change_pct"] = df_p["load_7d"].pct_change(1).round(3)

        df_p["fatigue_7d_mean"]  = df_p["fatigue_score"].rolling(7, min_periods=1).mean().round(2)
        df_p["soreness_7d_mean"] = df_p["muscle_soreness"].rolling(7, min_periods=1).mean().round(2)
        df_p["matches_last_14d"] = (df_p["day_type"] == "match").astype(int).rolling(14, min_periods=1).sum()

        # 个人z-score（相对自己历史基线）
        roll_mean = df_p["load_7d"].expanding().mean()
        roll_std  = df_p["load_7d"].expanding().std().fillna(1)
        df_p["individual_load_zscore"] = ((df_p["load_7d"] - roll_mean) / roll_std).round(3)

        # ── 真正的标签：未来7天内是否受伤 ── 
        # ── 用真实ACWR重新生成伤病事件 + 打标签 ──────────────────
        # ── 确定性标签生成（适合Demo数据集）──────────────────────────
        def compute_risk_score(row):
            acwr = row["acwr"] if pd.notna(row["acwr"]) else 1.0
            score = (
                3.0 * max(0, acwr - 1.3) +                          # ACWR超出安全区
                0.8 * max(0, row["fatigue_7d_mean"]  - 3.0) +       # 疲劳
                0.5 * max(0, row["soreness_7d_mean"] - 3.0) +       # 酸痛
                0.4 * min(row["previous_injury_count"], 5) * 0.2 +  # 历史伤病
                0.3 * max(0, row["individual_load_zscore"])          # 个人负荷偏高
            )
            return round(score, 4)

        # 只在比赛日/训练日计算风险（休息日不参与预测）
        active_mask = df_p["day_type"].isin(["match", "training"])
        df_p["_risk_score"] = 0.0
        df_p.loc[active_mask, "_risk_score"] = df_p[active_mask].apply(
            compute_risk_score, axis=1
        )

        # 风险分前7% → 标记为"未来7天内受伤"
        threshold = df_p.loc[active_mask, "_risk_score"].quantile(0.93)
        df_p["injury_next_7d"] = 0
        df_p.loc[active_mask, "injury_next_7d"] = (
            df_p.loc[active_mask, "_risk_score"] > threshold
        ).astype(int)

        # 加5%随机噪声（让数据更真实，避免AUC过于完美）
        noise_idx = df_p[active_mask].sample(frac=0.05, random_state=42).index
        df_p.loc[noise_idx, "injury_next_7d"] = (
            1 - df_p.loc[noise_idx, "injury_next_7d"]
        )

        # 生成injury_history（从标签反推，用于Dashboard展示）
        inj_rows = df_p[df_p["injury_next_7d"] == 1].copy()
        for _, row in inj_rows.iterrows():
            profile   = random.choice(INJURY_PROFILES)
            mech      = random.choices(MECHANISMS, weights=profile[2])[0]
            days_lost = int(np.random.choice(
                [3,7,14,21,28,42,60],
                p=[0.10,0.25,0.30,0.15,0.10,0.07,0.03]
            ))
            all_injuries.append({
                "injury_id":               f"INJ_{pid}_{len(all_injuries)+1:04d}",
                "player_id":               pid,
                "injury_start_date":       row["date"],
                "injury_end_date":         row["date"] + timedelta(days=days_lost),
                "injury_type":             profile[0],
                "body_location":           random.choice(profile[1]),
                "injury_mechanism":        mech,
                "days_lost":               days_lost,
                "return_to_training_date": row["date"] + timedelta(days=int(max(days_lost-3,1))),
            })

        # 排除标记
        season_end = df_p["date"].max()
        df_p["exclude_from_training"] = (
            df_p["date"] > season_end - timedelta(days=7)
        )
        df_p = df_p.drop(columns=["_risk_score"])
        
        all_daily.append(df_p)

    daily_df  = pd.concat(all_daily, ignore_index=True)
    injury_df = pd.DataFrame(all_injuries)

    # 加回球员基础信息
    daily_df = daily_df.merge(
        players[["player_id", "age", "position"]],
        on="player_id", how="left"
    )

    return daily_df, injury_df

# ─────────────────────────────────────────
# 6. 运行 & 保存
# ─────────────────────────────────────────
if __name__ == "__main__":
    daily_df, injury_df = generate_season(n_players=25, n_weeks=40)

    save_dir = os.path.dirname(os.path.abspath(__file__))
    daily_df.to_csv(os.path.join(save_dir, "daily_records.csv"), index=False)
    injury_df.to_csv(os.path.join(save_dir, "injury_history.csv"), index=False)

    # 数据质量检查
    print(f"daily_records : {daily_df.shape}  行 × 列")
    print(f"injury_history: {injury_df.shape}")
    print(f"\n标签分布（injury_next_7d）:")
    print(daily_df["injury_next_7d"].value_counts())
    print(f"\n伤病率: {daily_df['injury_next_7d'].mean():.2%}")
    print(f"平均每球员伤病次数: {len(injury_df)/25:.1f}")
    print(f"\nACWR 分布:\n{daily_df['acwr'].describe()}")