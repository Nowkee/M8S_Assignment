# Watch the three cases heal the same wound live, side by side
# Run with:  python live_view.py   (from a terminal or VS Code, not Jupyter)
# Run with:  python live_view.py gif   to save live_view.gif instead

import sys
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import ListedColormap
from swarm import Wound, draw_bots

SEED = 3   # change this to see a different wound
names = {"signal": "Signal following swarm", "random": "Random swarm", "none": "No nanobots"}
colours = {"signal": "#2a78d6", "random": "#eb6834", "none": "#898781"}
tissue = ListedColormap(["#f0efec", "#2a78d6", "#eb6834", "#1baf7a"])

models = {mode: Wound(mode, SEED) for mode in names}
fig, axes = plt.subplots(1, 4, figsize=(15, 4.2))
fig.text(0.5, 0.02, "grey = healthy, blue = damaged, orange = infected, "
         "green = healing      \u25B2 scout   \u25CF cleaner   \u25A0 carrier", ha="center", fontsize=9)


def update(frame):
    for ax, (mode, model) in zip(axes, models.items()):
        model.step()
        ax.clear()
        ax.imshow(model.state.T, cmap=tissue, vmin=0, vmax=3, origin="lower")
        draw_bots(ax, model)
        step = len(model.healed) - 1
        ax.set_title(f"{names[mode]}\nstep {step}, {model.healed[-1]:.0f}% healed", fontsize=9)
        ax.axis("off")

    # healing graph on the right
    graph = axes[3]
    graph.clear()
    for mode, model in models.items():
        graph.plot(model.healed, color=colours[mode], label=names[mode])
    graph.axhline(95, color="black", linestyle=":", linewidth=1)
    graph.set_xlim(0, 250)
    graph.set_ylim(0, 100)
    graph.set_xlabel("Time step")
    graph.set_ylabel("Wound healed (%)")
    graph.legend(loc="lower right", fontsize=7)


plt.subplots_adjust(left=0.02, right=0.98, top=0.85, bottom=0.18, wspace=0.25)
anim = FuncAnimation(fig, update, frames=250, interval=80, repeat=False, init_func=lambda: None)

if len(sys.argv) > 1 and sys.argv[1] == "gif":
    anim.save("live_view.gif", writer=PillowWriter(fps=15), dpi=80)
    print("Saved live_view.gif")
else:
    plt.show()
