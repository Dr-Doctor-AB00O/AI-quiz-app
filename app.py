"""AI Quiz Arena - DSC401-6 Artificial Intelligence (Units I & II).
Run with:  streamlit run app.py
"""
import json
import math
import os
import random
import time

import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI Quiz Arena", page_icon="🤖")

HERE = os.path.dirname(os.path.abspath(__file__))
LB_FILE = os.path.join(HERE, "leaderboard.json")
TYPES = {"M": "MCQ", "T": "True/False", "A": "Assertion–Reason", "F": "Fill in the blank",
         "X": "Match the following", "S": "Real-world scenario", "P": "Search / problem solving"}
DIFF = ["Easy", "Medium", "Hard"]
TIME_LIMIT = 30
ss = st.session_state


@st.cache_data
def load_questions():
    with open(os.path.join(HERE, "questions.json"), encoding="utf-8") as f:
        return json.load(f)


def load_lb():
    try:
        with open(LB_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_lb(rows):
    try:
        with open(LB_FILE, "w", encoding="utf-8") as f:
            json.dump(rows, f)
    except Exception:
        pass


def qtext(q):
    t = q["q"].replace("<br>", "  \n")
    return t.replace("|", "  \n") if q["t"] == "A" else t


# ---------- game logic ----------
def new_question():
    q = ss.qs[ss.i]
    order = list(range(len(q["o"])))
    if q["t"] not in ("T", "A"):
        random.shuffle(order)
    ss.order, ss.hid, ss.hint, ss.ans, ss.t0 = order, [], False, None, time.time()


def start(name, diff, n):
    pool = [q for q in load_questions() if diff < 0 or q["d"] == diff]
    random.shuffle(pool)
    ss.update(stage="quiz", name=name or "Player", qs=pool[:n], i=0, score=0, ok=0,
              streak=0, f=2, sk=1, miss=[], res=[], diff=diff)
    new_question()


def finish():
    ss.stage = "res"
    rows = load_lb()
    rows.append({"Name": ss.name, "Score": ss.score, "Accuracy %": round(100 * ss.ok / len(ss.qs)),
                 "Questions": len(ss.qs), "Level": "Mixed" if ss.diff < 0 else DIFF[ss.diff]})
    save_lb(sorted(rows, key=lambda r: -r["Score"])[:50])


def advance():
    ss.i += 1
    finish() if ss.i >= len(ss.qs) else new_question()


def answer(k):
    q = ss.qs[ss.i]
    left = max(0, TIME_LIMIT - (time.time() - ss.t0))
    ss.ans = k
    if k == q["a"]:
        ss.ok += 1
        ss.streak += 1
        ss.score += 10 + math.ceil(left / 6) + min(ss.streak - 1, 3) * 2
        ss.res.append(1)
    else:
        ss.streak = 0
        ss.miss.append(q)
        ss.res.append(0)


def fifty():
    q = ss.qs[ss.i]
    wrong = [k for k in ss.order if k != q["a"] and k not in ss.hid]
    if ss.f > 0 and len(wrong) > 2:
        ss.hid += random.sample(wrong, 2)
        ss.f -= 1


def skip():
    if ss.sk > 0:
        ss.sk -= 1
        ss.res.append(2)
        advance()


def hint():
    if not ss.hint:
        ss.hint = True
        ss.score = max(0, ss.score - 2)


# ---------- screens ----------
def menu():
    st.title("🤖 AI Quiz Arena")
    st.caption(f"Artificial Intelligence, Units I & II · {len(load_questions())} questions · 7 formats")
    with st.form("setup"):
        name = st.text_input("Your name", max_chars=20)
        level = st.selectbox("Difficulty", ["Mixed"] + DIFF)
        n = st.selectbox("Number of questions", [10, 25, "All"])
        if st.form_submit_button("Start quiz", type="primary"):
            start(name, -1 if level == "Mixed" else DIFF.index(level), 999 if n == "All" else n)
            st.rerun()
    st.info(f"{TIME_LIMIT} s per question · Lifelines: 50:50 (×2), Skip (×1), Hint (−2 points) · "
            "Faster answers and streaks score more.")


@st.fragment(run_every=1)
def timer():
    if ss.ans is not None:
        return
    left = int(TIME_LIMIT - (time.time() - ss.t0))
    if left <= 0:
        answer(-1)
        st.rerun(scope="app")
    st.metric("Time left", f"{left} s")


def quiz():
    q, n = ss.qs[ss.i], len(ss.qs)
    st.progress(ss.i / n, text=f"Question {ss.i + 1} of {n}")
    path = "".join("🟩" if r == 1 else "🟥" if r == 0 else "⬛" for r in ss.res)
    st.write(path + "🔵" + "⚪" * (n - len(ss.res) - 1))
    c1, c2, c3 = st.columns(3)
    c1.metric("Score", ss.score)
    c2.metric("Streak", ss.streak)
    with c3:
        timer()
    st.caption(f"{TYPES[q['t']]} · {DIFF[q['d']]}" + (f" · Topic: {q['tp']}" if ss.hint else ""))
    st.subheader(qtext(q))

    if ss.ans is None:
        opts = [k for k in ss.order if k not in ss.hid]
        st.radio("Choose one:", opts, index=None, format_func=lambda k: q["o"][k], key=f"r{ss.i}")
        st.button("Submit answer", type="primary",
                  disabled=ss.get(f"r{ss.i}") is None, on_click=lambda: answer(ss[f"r{ss.i}"]))
        a, b, c = st.columns(3)
        a.button(f"50:50 ({ss.f})", on_click=fifty)
        b.button(f"Skip ({ss.sk})", on_click=skip)
        c.button("Hint", on_click=hint)
    else:
        for k in ss.order:
            if k == q["a"]:
                st.success(q["o"][k])
            elif k == ss.ans:
                st.error(q["o"][k])
            else:
                st.write(f"▫️ {q['o'][k]}")
        verdict = "Correct!" if ss.ans == q["a"] else ("Time's up." if ss.ans < 0 else "Incorrect.")
        st.info(f"**{verdict}** {q['e']}")
        st.button("Next question" if ss.i + 1 < n else "See results", type="primary",
                  on_click=advance)


def results():
    n = len(ss.qs)
    pct = round(100 * ss.ok / n)
    st.title(f"{ss.name}: {ss.score} points")
    st.write(f"**{ss.ok} of {n} correct ({pct}%).** " +
             ("Excellent grasp of Units I and II." if pct >= 80 else
              "Good effort. Review the missed topics below." if pct >= 50 else
              "Revise Units I and II and try again."))
    if pct >= 80:
        st.balloons()
    st.button("Play again", type="primary", on_click=lambda: ss.update(stage="menu"))
    if ss.miss:
        st.subheader("Review missed questions")
        for q in ss.miss:
            with st.expander(q["q"].replace("<br>", " ").replace("|", " ")[:90]):
                st.write(qtext(q))
                st.success("Answer: " + q["o"][q["a"]])
                st.write(q["e"])


def bank():
    Q = load_questions()
    st.subheader(f"Question bank with answers ({len(Q)})")
    st.dataframe(pd.DataFrame([{
        "No": i + 1, "Type": TYPES[q["t"]], "Level": DIFF[q["d"]], "Topic": q["tp"],
        "Question": q["q"].replace("<br>", " ").replace("|", " "),
        "Options": " | ".join(q["o"]) if q["t"] not in ("A",) else "Standard A/R options",
        "Answer": q["o"][q["a"]], "Explanation": q["e"]} for i, q in enumerate(Q)]),
        hide_index=True)


def leaderboard():
    st.subheader("Leaderboard")
    rows = load_lb()
    if rows:
        st.dataframe(pd.DataFrame(rows[:10]), hide_index=True)
    else:
        st.write("No scores yet. Finish a quiz to appear here.")


def about():
    st.subheader("About this game")
    st.write("Built with **Python and Streamlit**. Covers agents, environments, problem spaces, "
             "uninformed and informed search, local search, CSP and means-end analysis.")
    st.write("**Scoring:** 10 points + speed bonus (up to 5) + streak bonus (up to 6). Hint costs 2 points.")
    st.write("**Progress path:** 🟩 correct, 🟥 wrong, ⬛ skipped, 🔵 current.")


ss.setdefault("stage", "menu")
tabs = st.tabs(["Play", "Question bank", "Leaderboard", "About"])
with tabs[0]:
    {"menu": menu, "quiz": quiz, "res": results}[ss.stage]()
with tabs[1]:
    bank()
with tabs[2]:
    leaderboard()
with tabs[3]:
    about()
