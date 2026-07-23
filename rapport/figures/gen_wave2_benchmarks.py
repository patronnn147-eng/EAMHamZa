"""Generates figures/wave2_benchmarks.png — plain-language Wave 2 explainer
(signal flow -> DST fusion -> health score, survival-model C-index benchmark,
agreement vs disagreement outcome) matching the chat widget shown to the user.
Run: python gen_wave2_benchmarks.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ---- palette (matches project's ML-service explainer color tokens) ----
BG        = "#EEF2F7"
CARD      = "#F6F9FC"
BORDER    = "#C8D5E2"
TEXT      = "#1A2232"
MUTED     = "#4E6880"
FAINT     = "#8FA5B8"
ACCENT    = "#E09500"
OK        = "#16A34A"
WARN      = "#D97706"

fig = plt.figure(figsize=(10.5, 14.5), dpi=200)
fig.patch.set_facecolor(BG)

def box(ax, x, y, w, h, title, sub, face=CARD, edge=BORDER, edge_w=1.2, title_c=TEXT, sub_c=MUTED, fs_t=11.5, fs_s=9.3):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012",
                        linewidth=edge_w, edgecolor=edge, facecolor=face, mutation_aspect=1)
    ax.add_patch(b)
    ax.text(x + w/2, y + h*0.64, title, ha="center", va="center", fontsize=fs_t, fontweight="bold", color=title_c)
    ax.text(x + w/2, y + h*0.28, sub, ha="center", va="center", fontsize=fs_s, color=sub_c, wrap=True)

def arrow(ax, x, y0, y1, color=FAINT):
    ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>", mutation_scale=16,
                                  linewidth=1.6, color=color))

# ============ PANEL 1 : flow diagram ============
ax1 = fig.add_axes([0.03, 0.70, 0.94, 0.27])
ax1.set_xlim(0, 1); ax1.set_ylim(0, 1); ax1.axis("off")
ax1.set_facecolor(BG)
ax1.text(0.0, 0.99, "1 — Four signals watch the machine, all the time", fontsize=13.5, fontweight="bold", color=TEXT, ha="left", va="top")
ax1.text(0.0, 0.91, "Each one asks a different question about the same sensor history", fontsize=10, color=MUTED, ha="left", va="top")

sig_w, sig_h, gap = 0.215, 0.26, 0.02
sig_y = 0.53
sigs = [
    ("Drift watch", "catches slow decline\n(CUSUM + Kalman)"),
    ("Distance from normal", "Mahalanobis\nHealth Index"),
    ("Survival odds", "Cox proportional\nhazards"),
    ("Physics check", "PINN — rejects\nimpossible RUL"),
]
x0 = 0.0
for i, (t, s) in enumerate(sigs):
    x = x0 + i * (sig_w + gap)
    box(ax1, x, sig_y, sig_w, sig_h, t, s, fs_t=10.5, fs_s=8.6)
    arrow(ax1, x + sig_w/2, sig_y, sig_y - 0.10)

fuse_w, fuse_h, fuse_y = 0.30, 0.15, 0.30
fuse_x = 0.5 - fuse_w/2
box(ax1, fuse_x, fuse_y, fuse_w, fuse_h, "Fusion", "combines all 4, flags disagreement\ninstead of guessing",
    face="#FBEBD2", edge=ACCENT, edge_w=1.8, fs_t=11, fs_s=8.6)
arrow(ax1, 0.5, fuse_y, fuse_y - 0.10)

out_w, out_h, out_y = 0.36, 0.15, 0.06
out_x = 0.5 - out_w/2
box(ax1, out_x, out_y, out_w, out_h, "Health score", "0–100 + Healthy / Degrading /\nCritical / Unknown",
    face="#FBEBD2", edge=ACCENT, edge_w=2.4, fs_t=11, fs_s=8.6)

# ============ PANEL 2 : benchmark bars ============
ax2 = fig.add_axes([0.08, 0.37, 0.86, 0.24])
ax2.set_facecolor(BG)
ax2.text(-0.06, 1.16, "2 — Does modeling machines-still-running actually help?", fontsize=13.5,
         fontweight="bold", color=TEXT, transform=ax2.transAxes, ha="left", va="top")
ax2.text(-0.06, 1.03, "C-index: how well the model ranks “fails soonest” vs “fails later” "
         "(higher = better, 0.5 = coin flip)", fontsize=10, color=MUTED, transform=ax2.transAxes, ha="left", va="top")

labels = ["Naive regression\n(ignores machines\nstill running)", "Cox proportional\nhazards", "Weibull AFT"]
values = [0.644, 0.712, 0.714]
colors = [BORDER, ACCENT, ACCENT]
xpos = [0, 1, 2]
ax2.bar(xpos, values, width=0.5, color=colors, edgecolor="none", zorder=3)
ax2.set_ylim(0, 0.85)
ax2.set_xlim(-0.6, 2.6)
for x, v in zip(xpos, values):
    ax2.text(x, v + 0.02, f"{v:.3f}", ha="center", fontsize=11, fontweight="bold", color=TEXT)
ax2.set_xticks(xpos)
ax2.set_xticklabels(labels, fontsize=8.8, color=MUTED)
ax2.axhline(0.5, color=FAINT, linewidth=1, linestyle=(0, (4, 3)))
ax2.text(2.62, 0.5, "coin flip", fontsize=8, color=FAINT, va="center")
for spine in ["top", "right", "left"]:
    ax2.spines[spine].set_visible(False)
ax2.spines["bottom"].set_color(BORDER)
ax2.tick_params(left=False, labelleft=False, bottom=False)
ax2.text(0.0, -0.28, "Yes — both survival models beat the naive baseline. Research prototype, same 100-machine test set as production.",
          fontsize=9, color=MUTED, transform=ax2.transAxes, ha="left", va="top")

# ============ PANEL 3 : agree / disagree cards ============
ax3 = fig.add_axes([0.03, 0.03, 0.94, 0.22])
ax3.set_xlim(0, 1); ax3.set_ylim(0, 1); ax3.axis("off")
ax3.set_facecolor(BG)
ax3.text(0.0, 0.97, "3 — What happens when the 4 signals disagree?", fontsize=13.5, fontweight="bold", color=TEXT, ha="left", va="top")

card_w, card_h, cgap, card_y = 0.47, 0.62, 0.04, 0.02
def card(ax, x, y, w, h, title, body, edge):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012",
                        linewidth=1.1, edgecolor=BORDER, facecolor=CARD)
    ax.add_patch(b)
    ax.add_patch(FancyBboxPatch((x, y), 0.012, h, boxstyle="square,pad=0", linewidth=0, facecolor=edge))
    ax.text(x + 0.035, y + h*0.74, title, fontsize=11, fontweight="bold", color=TEXT, ha="left", va="center")
    ax.text(x + 0.035, y + h*0.32, body, fontsize=9.3, color=MUTED, ha="left", va="center", wrap=True)

card(ax3, 0.0, card_y, card_w, card_h, "Mostly agree",
     "Fusion blends them normally → confident\nverdict (e.g. “Degrading, 72/100”).", OK)
card(ax3, card_w + cgap, card_y, card_w, card_h, "Strongly disagree",
     "Fusion refuses to force a fake consensus →\nverdict becomes “Unknown” instead of a\nwrong confident answer.", WARN)

fig.savefig("wave2_benchmarks.png", facecolor=BG, bbox_inches="tight", pad_inches=0.15)
print("saved wave2_benchmarks.png")
