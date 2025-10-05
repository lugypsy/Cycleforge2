
import streamlit as st
import pandas as pd

st.set_page_config(page_title="CycleForge", layout="wide")

# ------------------------------
# Fixed attack matrix (levels 1-20); level 0 => unusable (points=0)
# ------------------------------
MAG_POINTS = {
  1:300,2:330,3:365,4:400,5:440,6:485,7:535,8:590,9:650,10:715,
  11:785,12:865,13:950,14:1045,15:1150,16:1265,17:1390,18:1530,19:1685,20:1855
}
SB_POINTS = {
  1:700,2:850,3:1000,4:1150,5:1300,6:1450,7:1600,8:1750,9:1900,10:2050,
  11:2200,12:2300,13:2500,14:2650,15:2800,16:2950,17:3100,18:3250,19:3400,20:3550
}

def pts_mag(level:int)->int:
    return MAG_POINTS.get(level, 0) if level>0 else 0

def pts_sb(level:int)->int:
    return SB_POINTS.get(level, 0) if level>0 else 0

# ------------------------------
# Role definitions (casts, energy approx). Energy cap is enforced by role energy.
# ------------------------------
ROLES = {
    "SB-only": {"sb":3, "mag":0, "energy":21},
    "1 SB + 7 Mag": {"sb":1, "mag":7, "energy":21},
    "2 SB + 3 Mag": {"sb":2, "mag":3, "energy":20},
    "Mag-only": {"sb":0, "mag":10, "energy":20},
    "Idle": {"sb":0, "mag":0, "energy":0},
}

# ------------------------------
# Bracket role splits (from user's doc)
# ------------------------------
BRACKETS = {
    "25": {
        "recipe": {"SB_required":39, "Mag_required":123, "kills":40, "team_energy_used":"519 / 525"},
        "role_split": {"SB-only":10, "1 SB + 7 Mag":9, "Mag-only":6}
    },
    "19": {
        "recipe": {"SB_required":29, "Mag_required":93, "kills":30, "team_energy_used":"389 / 399"},
        "role_split": {"SB-only":5, "1 SB + 7 Mag":4, "Mag-only":5, "2 SB + 3 Mag":5}
    },
    # 13 has two options. Default to Opt 1; allow toggle.
    "13-opt1": {
        "recipe": {"SB_required":20, "Mag_required":66, "kills":21, "team_energy_used":"272 / 273"},
        "role_split": {"SB-only":4, "1 SB + 7 Mag":8, "Mag-only":1}
    },
    "13-opt2": {
        "recipe": {"SB_required":20, "Mag_required":66, "kills":21, "team_energy_used":"272 / 273"},
        "role_split": {"SB-only":3, "1 SB + 7 Mag":9, "2 SB + 3 Mag":1}
    }
}

# ------------------------------
# Sidebar controls
# ------------------------------
st.sidebar.title("CycleForge")
st.sidebar.caption("Round Cycle Planner")

bracket_choice = st.sidebar.selectbox("Bracket", ["13", "19", "25"], index=0)
if bracket_choice == "13":
    opt = st.sidebar.radio("13-city role layout", ["Opt 1","Opt 2"], index=0, horizontal=True)
    bracket_key = "13-opt1" if opt=="Opt 1" else "13-opt2"
else:
    bracket_key = bracket_choice

energy_cap = st.sidebar.number_input("Energy cap (per player)", min_value=1, max_value=50, value=21, step=1)
regen_info = st.sidebar.selectbox("Energy regeneration (info only)", ["1e / 3min"], index=0)

assign_btn = st.sidebar.button("Assign Roles", type="primary")
dl_placeholder = st.sidebar.empty()

# ------------------------------
# Roster Input
# ------------------------------
st.subheader("Roster Input")
st.caption("Enter player names and attack levels. Level 0 means the attack is unusable; both 0 => Idle.")

# Start with 10 placeholder rows: Player 1..Player 10, levels 0
default_players = [{"name": f"Player {i}", "sb_level": 0, "mag_level": 0} for i in range(1, 11)]

players_df = st.data_editor(
    pd.DataFrame(default_players),
    num_rows="dynamic",
    use_container_width=True,
    key="players_editor"
)

# ------------------------------
# Cycle Recipe & Feasibility
# ------------------------------
st.subheader("Cycle Recipe & Feasibility")

recipe = BRACKETS[bracket_key]["recipe"]
role_split = BRACKETS[bracket_key]["role_split"]

colA, colB = st.columns(2)

with colA:
    st.markdown("**Bracket recipe:**")
    st.write(f"- SB casts required: **{recipe['SB_required']}**")
    st.write(f"- Mag casts required: **{recipe['Mag_required']}**")
    st.write(f"- Expected kills: **{recipe['kills']}**")
    st.write(f"- Energy used (team): **{recipe['team_energy_used']}**")
    # Placeholders for expected points (filled post-assignment)
    exp_mag_points = st.markdown("- Expected Mag points (team total): —")
    exp_sb_points = st.markdown("- Expected SB points (team total): —")
    exp_total_points = st.markdown("- Expected grand total (Mag + SB): —")

with colB:
    st.markdown("**Roster capability:**")
    sb_capable = int((players_df["sb_level"]>0).sum()) if "sb_level" in players_df else 0
    mag_capable = int((players_df["mag_level"]>0).sum()) if "mag_level" in players_df else 0
    st.write(f"- SB-capable players: **{sb_capable}** (sb_level > 0)")
    st.write(f"- Mag-capable players: **{mag_capable}** (mag_level > 0)")
    role_counts_placeholder = st.empty()

st.markdown("---")

# ------------------------------
# Helper: compute role score for a player
# ------------------------------
def pts_mag(level:int)->int:
    return MAG_POINTS.get(level, 0) if level>0 else 0

def pts_sb(level:int)->int:
    return SB_POINTS.get(level, 0) if level>0 else 0

def role_score(row, role_name, energy_cap):
    r = ROLES[role_name]
    # Check energy feasibility
    if r["energy"] > energy_cap:  # cannot exceed cap
        return None  # infeasible
    # Check attack feasibility
    if r["sb"]>0 and int(row["sb_level"])<=0:
        return None
    if r["mag"]>0 and int(row["mag_level"])<=0:
        return None
    # Points
    sb_pts = pts_sb(int(row["sb_level"])) * r["sb"]
    mag_pts = pts_mag(int(row["mag_level"])) * r["mag"]
    total = sb_pts + mag_pts
    return {
        "role": role_name,
        "sb_casts": r["sb"],
        "mag_casts": r["mag"],
        "energy_used": r["energy"],
        "sb_points": sb_pts,
        "mag_points": mag_pts,
        "player_points": total
    }

# ------------------------------
# Assignment: greedy per role type using the fixed role_split
# ------------------------------
def assign_roles(players_df, role_split, energy_cap):
    df = players_df.copy()
    df["sb_level"] = df["sb_level"].fillna(0).astype(int)
    df["mag_level"] = df["mag_level"].fillna(0).astype(int)

    df["pts_per_sb"] = df["sb_level"].apply(lambda x: pts_sb(int(x)) if int(x)>0 else 0)
    df["pts_per_mag"] = df["mag_level"].apply(lambda x: pts_mag(int(x)) if int(x)>0 else 0)

    assigned = []
    used_players = set()

    # For each role type and its required count, pick best available players for that role
    for role_name, count in role_split.items():
        candidates = []
        for idx, row in df.iterrows():
            if idx in used_players: 
                continue
            sc = role_score(row, role_name, energy_cap)
            if sc is not None:
                candidates.append((idx, sc["player_points"], sc))
        candidates.sort(key=lambda x: x[1], reverse=True)
        for i in range(min(count, len(candidates))):
            idx, _, sc = candidates[i]
            used_players.add(idx)
            assigned.append((idx, role_name, sc))

    # Remaining players -> try Mag-only if feasible; else Idle
    for idx, row in df.iterrows():
        if idx in used_players:
            continue
        sc_mag = role_score(row, "Mag-only", energy_cap)
        if sc_mag is not None and (row["mag_level"]>0):
            assigned.append((idx, "Mag-only", sc_mag))
        else:
            assigned.append((idx, "Idle", {"role":"Idle","sb_casts":0,"mag_casts":0,"energy_used":0,"sb_points":0,"mag_points":0,"player_points":0}))

    # Build output in the locked column order
    output_rows = []
    for idx, role_name, sc in assigned:
        row = df.loc[idx]
        output_rows.append({
            "name": row["name"],
            "sb_level": int(row["sb_level"]),
            "mag_level": int(row["mag_level"]),
            "role": role_name,
            "pts_per_sb": df.loc[idx, "pts_per_sb"],
            "pts_per_mag": df.loc[idx, "pts_per_mag"],
            "sb_casts": sc["sb_casts"],
            "mag_casts": sc["mag_casts"],
            "sb_points": sc["sb_points"],
            "mag_points": sc["mag_points"],
            "player_points": sc["player_points"],
            "energy_used": sc["energy_used"],
        })
    out_df = pd.DataFrame(output_rows)
    role_counts = out_df["role"].value_counts().to_dict()
    return out_df, role_counts

plan_df = None
role_counts = {}

if assign_btn:
    if not all(col in players_df.columns for col in ["name","sb_level","mag_level"]):
        st.error("Please include columns: name, sb_level, mag_level.")
    else:
        try:
            plan_df, role_counts = assign_roles(players_df, role_split, energy_cap)

            # Post-assign expected points
            total_mag_points = int(plan_df["mag_points"].sum())
            total_sb_points = int(plan_df["sb_points"].sum())
            total_points = int(plan_df["player_points"].sum())
            exp_mag_points.markdown(f"- Expected Mag points (team total): **{total_mag_points:,}**")
            exp_sb_points.markdown(f"- Expected SB points (team total): **{total_sb_points:,}**")
            exp_total_points.markdown(f"- Expected grand total (Mag + SB): **{total_points:,}**")

            # Update role counts view
            with role_counts_placeholder:
                st.write("- SB-only players:", role_counts.get("SB-only",0))
                st.write("- Mag-only players:", role_counts.get("Mag-only",0))
                st.write("- 2 SB / 3 Mag players:", role_counts.get("2 SB + 3 Mag",0))
                st.write("- 1 SB / 7 Mag players:", role_counts.get("1 SB + 7 Mag",0))

        except Exception as e:
            st.error(f"Assignment failed: {e}")

# ------------------------------
# Plan Details table + download
# ------------------------------
st.subheader("Plan Details")
locked_order = ["name","sb_level","mag_level","role","pts_per_sb","pts_per_mag","sb_casts","mag_casts","sb_points","mag_points","player_points","energy_used"]

if plan_df is not None:
    plan_df = plan_df[locked_order]
    st.dataframe(plan_df, use_container_width=True, hide_index=True)
    csv = plan_df.to_csv(index=False).encode("utf-8")
    dl_placeholder.download_button("Download Plan CSV", data=csv, file_name="Plan.csv", mime="text/csv")
else:
    st.info("Click 'Assign Roles' to generate the plan.")
