# Nanobot swarm healing a skin wound, simple agent based model with Mesa
# Compares: signal following swarm, randomly moving swarm, no nanobots
# Run with:  python swarm.py

import numpy as np
import matplotlib.pyplot as plt
import mesa

HEALTHY, DAMAGED, INFECTED, HEALING = 0, 1, 2, 3
SIZE = 40          # grid is 40 x 40 squares
N_BOTS = 100       # swarm size
MAX_STEPS = 400    # stop here if the wound has not healed
RUNS = 20          # repeats for each condition


def spread(field):
    # each square shares its chemical with its 8 neighbours, then it fades a bit
    p = np.pad(field, 1)
    around = (p[:-2, :-2] + p[:-2, 1:-1] + p[:-2, 2:] + p[1:-1, :-2] +
              p[1:-1, 2:] + p[2:, :-2] + p[2:, 1:-1] + p[2:, 2:]) / 8
    return (0.5 * field + 0.5 * around) * 0.95


class Nanobot(mesa.Agent):
    def __init__(self, model, role):
        super().__init__(model)
        self.role = role          # "scout", "cleaner" or "carrier"
        self.fuel = 300           # rule 5: limited fuel
        self.medicine = 30        # rule 5: limited medicine

    def work(self):
        x, y = self.pos
        m = self.model
        if self.role == "scout" and m.state[x, y] != HEALTHY:
            m.marker[x, y] += 2                       # leave a trail for the others
        elif self.role == "cleaner" and m.state[x, y] == INFECTED:
            m.bacteria[x, y] -= 0.2                   # kill bacteria
            self.medicine -= 1
            return True
        elif self.role == "carrier" and m.state[x, y] in (DAMAGED, HEALING):
            m.heal[x, y] += 0.25                      # rule 3: only on clean squares
            m.state[x, y] = HEALING
            self.medicine -= 1
            return True
        return False

    def move(self):
        m = self.model
        options = m.grid.get_neighborhood(self.pos, moore=True)
        # random swarm, or a small random step to explore (rule 1)
        if m.mode == "random" or self.random.random() < 0.15:
            m.grid.move_agent(self, self.random.choice(options))
            return
        # rule 1: go where the signal is strongest
        # rule 2: squares that already have bots are less attractive
        def score(cell):
            crowd = len(m.grid.get_cell_list_contents([cell]))
            return m.signal[cell] + m.marker[cell] - 0.3 * crowd
        best = max(score(c) for c in options)
        m.grid.move_agent(self, self.random.choice([c for c in options if score(c) == best]))

    def step(self):
        if not self.work():
            self.move()
        self.fuel -= 1
        if self.fuel <= 0 or self.medicine <= 0:   # rule 5: breaks down safely
            self.model.grid.remove_agent(self)
            self.remove()


class Wound(mesa.Model):
    def __init__(self, mode="signal", seed=None):
        super().__init__(rng=seed)
        self.mode = mode
        self.grid = mesa.space.MultiGrid(SIZE, SIZE, torus=False)

        # oval wound in the middle with four infected patches
        x, y = np.meshgrid(np.arange(SIZE), np.arange(SIZE), indexing="ij")
        self.wound = ((x - 20) / 12) ** 2 + ((y - 20) / 9) ** 2 <= 1
        self.state = np.where(self.wound, DAMAGED, HEALTHY)
        self.bacteria = np.zeros((SIZE, SIZE))
        self.heal = np.zeros((SIZE, SIZE))
        self.signal = np.zeros((SIZE, SIZE))
        self.marker = np.zeros((SIZE, SIZE))
        cells = np.argwhere(self.wound)
        for _ in range(4):
            cx, cy = cells[self.rng.integers(len(cells))]
            patch = ((x - cx) ** 2 + (y - cy) ** 2 <= 9) & self.wound
            self.state[patch] = INFECTED
            self.bacteria[patch] = 0.6

        # bots start in a gel around the edge of the wound
        if mode != "none":
            edge = np.argwhere((spread(spread(self.wound * 1.0)) > 0) & ~self.wound)
            roles = ["scout"] * 20 + ["cleaner"] * 40 + ["carrier"] * 40
            for role in roles:
                cx, cy = edge[self.rng.integers(len(edge))]
                self.grid.place_agent(Nanobot(self, role), (int(cx), int(cy)))

        self.healed = [0.0]

    def update_tissue(self):
        inf = self.state == INFECTED
        # bacteria grow, and the body slowly kills some by itself
        self.bacteria[inf] += 0.02 * self.bacteria[inf] * (1 - self.bacteria[inf]) - 0.004
        cleaned = inf & (self.bacteria <= 0)
        self.state[cleaned] = DAMAGED
        self.bacteria[cleaned] = 0

        # infection can jump to open neighbours
        open_wound = (self.state == DAMAGED) | (self.state == HEALING)
        pressure = spread(np.where(self.state == INFECTED, self.bacteria, 0)) * 8
        new = open_wound & (self.rng.random((SIZE, SIZE)) < 0.01 * pressure)
        self.state[new] = INFECTED
        self.bacteria[new] = 0.3
        self.heal[new] = 0

        # the body heals slowly from the healthy edges inwards
        healthy_near = spread((self.state == HEALTHY) * 1.0) > 0.05
        edge = open_wound & ~new & healthy_near
        self.heal[edge] += 0.02 * self.rng.uniform(0.5, 1.5, edge.sum())
        self.state[edge] = HEALING

        done = (self.heal >= 1) & (self.state != INFECTED)
        self.state[done] = HEALTHY

    def step(self):
        self.update_tissue()
        # rule 4: only unhealed squares give off a signal
        self.signal = spread(self.signal + (self.state != HEALTHY))
        self.marker = spread(self.marker) * (self.state != HEALTHY)
        self.agents.shuffle_do("step")
        self.healed.append((self.state[self.wound] == HEALTHY).mean() * 100)


def draw_bots(ax, model):
    # each type of nanobot gets its own shape
    shapes = {"scout": "^", "cleaner": "o", "carrier": "s"}
    for role, shape in shapes.items():
        spots = [a.pos for a in model.agents if a.role == role]
        if spots:
            x, y = zip(*spots)
            ax.scatter(x, y, s=22, marker=shape, c="black", edgecolors="white", linewidths=0.4)


def healing_time(model):
    # steps until 95% of the wound is healthy (None if it never gets there)
    for t, h in enumerate(model.healed):
        if h >= 95:
            return t
    return None


if __name__ == "__main__":
    results = {}
    for mode in ["signal", "random", "none"]:
        curves, times = [], []
        for seed in range(RUNS):
            model = Wound(mode, seed)
            for _ in range(MAX_STEPS):
                model.step()
            curves.append(model.healed)
            times.append(healing_time(model))
        results[mode] = (np.array(curves), times)

        done = [t for t in times if t is not None]
        final = np.array(curves)[:, -1]
        print(f"{mode:7s} healed in {len(done)}/{RUNS} runs | "
              f"mean time {np.mean(done) if done else float('nan'):.1f} "
              f"(sd {np.std(done) if done else float('nan'):.1f}, "
              f"min {min(done) if done else '-'}, max {max(done) if done else '-'}) | "
              f"healed at end {final.mean():.1f}%")

    # graph of healing over time
    names = {"signal": "Signal following swarm", "random": "Random swarm", "none": "No nanobots"}
    colours = {"signal": "#2a78d6", "random": "#eb6834", "none": "#898781"}
    plt.figure(figsize=(7, 4))
    for mode, (curves, _) in results.items():
        plt.plot(curves.mean(axis=0), color=colours[mode], linewidth=2, label=names[mode])
        plt.fill_between(range(MAX_STEPS + 1), np.percentile(curves, 10, axis=0),
                         np.percentile(curves, 90, axis=0), color=colours[mode], alpha=0.15)
    plt.axhline(95, color="black", linestyle=":", linewidth=1)
    plt.xlabel("Time step")
    plt.ylabel("Wound healed (%)")
    plt.title("Average of 20 runs (shaded band shows the 10th to 90th percentile)", fontsize=10)
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig("healing_curves.png", dpi=150)

    # pictures of one run of each condition
    colours_map = plt.matplotlib.colors.ListedColormap(["#f0efec", "#2a78d6", "#eb6834", "#1baf7a"])
    fig, axes = plt.subplots(3, 4, figsize=(10, 7.8))
    for row, mode in enumerate(["signal", "random", "none"]):
        model = Wound(mode, seed=3)
        for col, stop in enumerate([0, 30, 60, 150]):
            while len(model.healed) - 1 < stop:
                model.step()
            ax = axes[row, col]
            ax.imshow(model.state.T, cmap=colours_map, vmin=0, vmax=3, origin="lower")
            draw_bots(ax, model)
            ax.set_title(f"{names[mode]}, step {stop}\n{model.healed[-1]:.0f}% healed", fontsize=8)
            ax.axis("off")
    fig.text(0.5, 0.01, "grey = healthy, blue = damaged, orange = infected, "
             "green = healing      \u25B2 scout   \u25CF cleaner   \u25A0 carrier", ha="center", fontsize=9)
    plt.tight_layout(rect=(0, 0.03, 1, 1))
    plt.savefig("snapshots.png", dpi=150)
    print("Saved healing_curves.png and snapshots.png")
