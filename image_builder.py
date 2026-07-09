"""
Renders a clean "study card" PNG for a CSS subject/topic using matplotlib.
Matplotlib ships its own DejaVu Sans font, so this works reliably on a bare
GitHub Actions runner with no extra font installation -- unlike PIL with
system fonts, which can't be relied on to exist on ubuntu-latest.
"""
import os
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import config


def build_topic_card(subject: str, topic: str, outline: dict) -> str:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    safe_name = "".join(c if c.isalnum() else "_" for c in topic)[:40]
    filepath = os.path.join(config.OUTPUT_DIR, f"topic_{safe_name}.png")

    heading = outline.get("heading", topic)
    points = outline.get("points", [])[:7]

    fig, ax = plt.subplots(figsize=(8, 10), dpi=150)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12.5)
    ax.axis("off")

    # Background
    ax.add_patch(patches.Rectangle((0, 0), 10, 12.5, facecolor="#0f2942", zorder=0))
    ax.add_patch(patches.Rectangle((0, 10.8), 10, 1.7, facecolor="#16406b", zorder=1))

    # Header text
    ax.text(5, 11.9, "CSS / FIA STUDY CARD", ha="center", va="center",
             fontsize=13, color="#8fc7ff", weight="bold", zorder=2)
    ax.text(5, 11.2, subject.upper(), ha="center", va="center",
             fontsize=15, color="white", weight="bold", zorder=2)

    # Topic heading box
    wrapped_heading = "\n".join(textwrap.wrap(heading, width=28))
    ax.add_patch(patches.FancyBboxPatch(
        (0.5, 9.2), 9, 1.3, boxstyle="round,pad=0.15",
        facecolor="#f2a900", edgecolor="none", zorder=2))
    ax.text(5, 9.85, wrapped_heading, ha="center", va="center",
             fontsize=15, color="#0f2942", weight="bold", zorder=3)

    # Bullet points
    y = 8.4
    for point in points:
        wrapped = textwrap.wrap(point, width=48)
        ax.add_patch(patches.Circle((0.9, y - 0.15), 0.08, facecolor="#f2a900", zorder=2))
        for i, line in enumerate(wrapped):
            ax.text(1.25, y - (i * 0.42), line, ha="left", va="center",
                     fontsize=11.5, color="white", zorder=2)
        y -= (0.42 * max(1, len(wrapped))) + 0.35

    # Footer
    ax.add_patch(patches.Rectangle((0, 0), 10, 0.6, facecolor="#16406b", zorder=1))
    ax.text(5, 0.3, "Daily CSS/FIA Prep Agent", ha="center", va="center",
             fontsize=9, color="#8fc7ff", zorder=2)

    fig.savefig(filepath, bbox_inches="tight", facecolor="#0f2942")
    plt.close(fig)
    return filepath
