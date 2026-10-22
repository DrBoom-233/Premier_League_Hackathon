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
def daily_workload(day_type: str, fitness: float):
    """根据日类型返回当天的外部负荷指标（分钟、距离、加减速次数等）"""
    if day_type == "rest":
        return dict(
            match_minutes=0, training_minutes=0,
            total_distance=0, hsr_distance=0, sprint_distance=0,
            acceleration_count=0, deceleration_count=0,
            max_speed=0, session_rpe=0, srpe_load=0,
        )
    if day_type == "match":
        mins = np.random.randint(45, 96)
        total_d = np.random.normal(10500, 800) * fitness
        return dict(
            match_minutes=mins,
            training_minutes=0,
            total_distance=max(0, round(total_d)),
            hsr_distance=max(0, round(np.random.normal(900, 150))),
            sprint_distance=max(0, round(np.random.normal(350, 80))),
            acceleration_count=np.random.randint(25, 55),
            deceleration_count=np.random.randint(20, 50),
            max_speed=round(np.random.normal(29, 2.5), 1),
            session_rpe=round(np.random.uniform(6.5, 9.5), 1),
            srpe_load=round(mins * np.random.uniform(6.5, 9.5), 1),
        )
    # training
    mins = np.random.randint(60, 105)
    intensity = np.random.uniform(0.5, 1.0)
    total_d = np.random.normal(6500, 700) * fitness * intensity
    rpe = round(np.random.uniform(3, 8) * intensity, 1)
    return dict(
        match_minutes=0,
        training_minutes=mins,
        total_distance=max(0, round(total_d)),
        hsr_distance=max(0, round(np.random.normal(400, 100) * intensity)),
        sprint_distance=max(0, round(np.random.normal(120, 40) * intensity)),
        acceleration_count=np.random.randint(10, 35),
        deceleration_count=np.random.randint(8, 30),
        max_speed=round(np.random.normal(24, 2), 1),
        session_rpe=rpe,
        srpe_load=round(mins * rpe, 1),
    )

def daily_wellness(day_type: str, fatigue_carry: float):
    """
    恢复 & 健康问卷（1=最差，5=最好）
    fatigue_carry: 上一天累积疲劳程度，影响今天的wellness
    clip到合理范围，避免出现极端值
    """
    base_fatigue = 3.0 - fatigue_carry * 1.5   # 疲劳越高，wellness越差
    return dict(
        sleep_duration=round(np.clip(np.random.normal(7.2, 0.8), 4, 10), 1),
        sleep_quality= int(np.clip(np.random.normal(3.5 - fatigue_carry, 0.7), 1, 5)),
        fatigue_score= int(np.clip(np.random.normal(base_fatigue, 0.8), 1, 5)),
        muscle_soreness=int(np.clip(np.random.normal(
            3.5 if day_type == "match" else 2.5, 0.9) + fatigue_carry, 1, 5)),
        stress_level=  int(np.clip(np.random.normal(2.5, 0.8), 1, 5)),
        resting_hr=    round(np.clip(np.random.normal(58 + fatigue_carry*6, 5), 42, 90)),
        hrv_rmssd=     round(np.clip(np.random.normal(65 - fatigue_carry*10, 10), 20, 120), 1),
    )

# ─────────────────────────────────────────
# 4. 核心：伤病概率函数
# ─────────────────────────────────────────
def injury_probability(acwr, fatigue_7d, soreness_7d,
                        prev_injuries, days_since_injury,
                        day_type, injury_prone):
    """
    依据运动科学文献的伤病风险因子加权计算概率
    基础受伤率: 约每球员每赛季1.5次 ≈ 每场比赛0.004
    """
    if day_type not in ("match", "training"):
        return 0.0

    base = 0.004 if day_type == "match" else 0.001

    # ACWR风险（甜区 0.8~1.3，>1.5高风险）
    if   acwr is None or np.isnan(acwr): acwr_mult = 1.0
    elif acwr < 0.8:   acwr_mult = 1.3   # 欠训练也有风险
    elif acwr <= 1.3:  acwr_mult = 1.0   # 理想区间
    elif acwr <= 1.5:  acwr_mult = 1.5
    elif acwr <= 2.0:  acwr_mult = 2.5   # 高风险
    else:              acwr_mult = 4.0   # 极高风险

    # 疲劳（1最好5最差，评分越高风险越高）
    fatigue_mult = 1 + (fatigue_7d - 3) * 0.3

    # 肌肉酸痛
    soreness_mult = 1 + (soreness_7d - 3) * 0.2

    # 历史伤病（每次+20%风险）
    history_mult = 1 + min(prev_injuries, 5) * 0.2

    # 刚从伤病回来（30天内复发率更高）
    recency_mult = 1.8 if days_since_injury < 30 else 1.0

    p = base * acwr_mult * fatigue_mult * soreness_mult * \
        history_mult * recency_mult * (1 + injury_prone)

    return min(p, 0.15)   # 单日上限15%

# ─────────────────────────────────────────
# 5. 主生成函数
# ─────────────────────────────────────────
INJURY_TYPES    = ["Hamstring", "Ankle", "Knee", "Groin", "Calf", "Quad", "Back"]
BODY_LOCATIONS  = ["Left Hamstring", "Right Hamstring", "Left Ankle", "Right Ankle",
                   "Left Knee", "Right Knee", "Groin", "Lower Back", "Left Calf", "Right Calf"]
MECHANISMS      = ["Non-contact", "Contact", "Unknown"]

def generate_season(n_players=25, n_weeks=40,
                    start_date=date(2025, 8, 1)):
    players   = generate_squad(n_players)
    calendar  = build_season_calendar(start_date, n_weeks)

    all_daily    = []
    all_injuries = []

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

            wl  = daily_workload(day_type, player["base_fitness"])
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

            # ── 伤病发生判断（发生在这天之后） ──
            if not is_injured and day_type in ("match", "training"):
                # acwr在滚动窗口计算，这里先用fatigue_carry近似
                approx_acwr = 1.0 + fatigue_carry * 0.5
                p = injury_probability(
                    acwr=approx_acwr,
                    fatigue_7d=wel["fatigue_score"],
                    soreness_7d=wel["muscle_soreness"],
                    prev_injuries=injury_history_count,
                    days_since_injury=days_since_inj,
                    day_type=day_type,
                    injury_prone=player["injury_prone"],
                )
                if random.random() < p:
                    days_lost = int(np.random.choice(
                        [3,7,14,21,28,42,60],
                        p=[0.10,0.25,0.30,0.15,0.10,0.07,0.03]
                    ))
                    inj_mechanism = np.random.choice(
                        MECHANISMS,
                        p=[0.65, 0.25, 0.10]   # 非接触伤病为主
                    )
                    all_injuries.append({
                        "injury_id":             f"INJ_{pid}_{len(all_injuries)+1:04d}",
                        "player_id":             pid,
                        "injury_start_date":     d,
                        "injury_end_date":       d + timedelta(days=days_lost),
                        "injury_type":           random.choice(INJURY_TYPES),
                        "body_location":         random.choice(BODY_LOCATIONS),
                        "injury_mechanism":      inj_mechanism,
                        "days_lost":             days_lost,
                        "return_to_training_date": d + timedelta(days=int(max(days_lost-3, 1))),
                    })
                    injury_history_count += 1
                    last_injury_date     =  d
                    is_injured           =  True
                    injury_return_date   =  d + timedelta(days=days_lost)

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
        injury_dates = set(
            inj["injury_start_date"]
            for inj in all_injuries
            if inj["player_id"] == pid
        )
        def has_injury_next_7d(row_date):
            return int(any(
                row_date < inj_d <= row_date + timedelta(days=7)
                for inj_d in injury_dates
            ))
        df_p["injury_next_7d"] = df_p["date"].apply(has_injury_next_7d)

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