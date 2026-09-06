import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from html import escape


USERNAME = "Iarlei-Barros"
OUTPUT_FILE = "assets/activity-skyline.svg"

DAYS = 180
TOWERS = 18


# ============================================================
# GITHUB GRAPHQL
# ============================================================

def get_contributions():
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        raise RuntimeError("GITHUB_TOKEN não encontrado.")

    today = datetime.now(timezone.utc).date()
    from_date = today - timedelta(days=DAYS - 1)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(
          from: $from
          to: $to
        ) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    variables = {
        "login": USERNAME,
        "from": f"{from_date.isoformat()}T00:00:00Z",
        "to": f"{today.isoformat()}T23:59:59Z",
    }

    payload = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": USERNAME,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Erro ao consultar GitHub GraphQL: {error.code}\n{body}"
        )

    if "errors" in data:
        raise RuntimeError(
            "GitHub GraphQL retornou erros:\n"
            + json.dumps(data["errors"], indent=2)
        )

    user = data.get("data", {}).get("user")

    if not user:
        raise RuntimeError(
            f"Usuário '{USERNAME}' não encontrado ou sem acesso."
        )

    calendar = user["contributionsCollection"]["contributionCalendar"]

    days = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append({
                "date": day["date"],
                "count": day["contributionCount"]
            })

    days = sorted(days, key=lambda x: x["date"])

    return days, calendar["totalContributions"]


# ============================================================
# AGREGAÇÃO
# ============================================================

def create_towers(days):
    """
    Divide os últimos 180 dias em 18 períodos.
    Cada torre representa aproximadamente 10 dias.
    """

    if not days:
        return [0] * TOWERS

    # Mantém exatamente os últimos DAYS dias
    days = days[-DAYS:]

    towers = []

    base_size = len(days) // TOWERS
    remainder = len(days) % TOWERS

    index = 0

    for i in range(TOWERS):
        size = base_size

        if i < remainder:
            size += 1

        chunk = days[index:index + size]

        total = sum(day["count"] for day in chunk)

        towers.append(total)

        index += size

    return towers


# ============================================================
# CORES TOKYO NIGHT
# ============================================================

def tower_level(value, maximum):
    if value <= 0:
        return "zero"

    if maximum <= 0:
        return "low"

    ratio = value / maximum

    if ratio <= 0.25:
        return "low"

    if ratio <= 0.55:
        return "mid"

    if ratio <= 0.80:
        return "high"

    return "peak"


def tower_color(level):
    colors = {
        "zero": {
            "front": "#292e42",
            "side": "#1f2335",
            "top": "#3b4261",
        },

        "low": {
            "front": "#3d59a1",
            "side": "#293b73",
            "top": "#7aa2f7",
        },

        "mid": {
            "front": "#236b7a",
            "side": "#174b58",
            "top": "#7dcfff",
        },

        "high": {
            "front": "#6d3aa8",
            "side": "#4c2778",
            "top": "#bb9af7",
        },

        "peak": {
            "front": "#b44c70",
            "side": "#7a3152",
            "top": "#f7768e",
        },
    }

    return colors[level]


# ============================================================
# SVG
# ============================================================

def tower_svg(x, base_y, width, height, depth, colors, glow=False):
    """
    Cria uma torre 3D:

              top
             /---/
            /   /
        front   side
    """

    top_y = base_y - height

    x2 = x + width
    xd = x2 + depth

    top_shift = 6

    front = f"""
    <polygon
        points="{x},{base_y} {x2},{base_y} {x2},{top_y} {x},{top_y}"
        fill="{colors['front']}"/>
    """

    side = f"""
    <polygon
        points="{x2},{base_y} {xd},{base_y - top_shift} {xd},{top_y - top_shift} {x2},{top_y}"
        fill="{colors['side']}"/>
    """

    top = f"""
    <polygon
        points="{x},{top_y} {x2},{top_y} {xd},{top_y - top_shift} {x + depth},{top_y - top_shift}"
        fill="{colors['top']}"/>
    """

    glow_svg = ""

    if glow:
        glow_svg = f"""
        <polygon
            points="{x},{top_y} {x2},{top_y} {xd},{top_y - top_shift} {x + depth},{top_y - top_shift}"
            fill="none"
            stroke="{colors['top']}"
            stroke-width="1.5"
            filter="url(#neon)"/>
        """

    return front + side + top + glow_svg


# ============================================================
# SVG COMPLETO
# ============================================================

def generate_svg(days, total_contributions, towers):
    width = 900
    height = 320

    chart_x = 35
    chart_width = 500
    chart_base = 270

    maximum = max(towers) if towers else 0

    tower_width = 23
    depth = 11
    spacing = 28

    # Divide as torres em duas fileiras
    back_count = 9
    front_count = 9

    # Alturas
    min_height = 18
    max_height = 150

    def calculate_height(value):
        if maximum <= 0 or value <= 0:
            return min_height

        ratio = value / maximum

        return int(
            min_height
            + ratio * (max_height - min_height)
        )

    # Dias ativos
    active_days = sum(
        1 for day in days
        if day["count"] > 0
    )

    # Maior período
    peak_index = 0

    if towers:
        peak_index = towers.index(max(towers))

    peak_value = towers[peak_index] if towers else 0

    # Ano atual
    current_year = datetime.now(timezone.utc).year

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 {width} {height}"
    width="{width}"
    height="{height}"
    role="img"
    aria-label="Contribution Skyline de {USERNAME}">

    <defs>

        <!-- Tokyo Night -->

        <linearGradient
            id="sky"
            x1="0"
            y1="0"
            x2="0"
            y2="1">

            <stop
                offset="0%"
                stop-color="#1a1b26"/>

            <stop
                offset="55%"
                stop-color="#16161e"/>

            <stop
                offset="100%"
                stop-color="#0f111a"/>

        </linearGradient>


        <radialGradient
            id="glow"
            cx="0.45"
            cy="1"
            r="0.7">

            <stop
                offset="0%"
                stop-color="#bb9af7"
                stop-opacity="0.28"/>

            <stop
                offset="100%"
                stop-color="#bb9af7"
                stop-opacity="0"/>

        </radialGradient>


        <filter id="neon">

            <feGaussianBlur
                stdDeviation="2.5"
                result="blur"/>

            <feMerge>

                <feMergeNode in="blur"/>

                <feMergeNode in="SourceGraphic"/>

            </feMerge>

        </filter>

    </defs>


    <!-- BACKGROUND -->

    <rect
        width="{width}"
        height="{height}"
        fill="url(#sky)"/>


    <!-- STARS -->

    <g fill="#c0caf5">

        <circle cx="70" cy="35" r="0.8"/>
        <circle cx="160" cy="22" r="1"/>
        <circle cx="260" cy="50" r="0.7"/>
        <circle cx="380" cy="28" r="1.1"/>
        <circle cx="510" cy="58" r="0.8"/>
        <circle cx="650" cy="32" r="1"/>
        <circle cx="780" cy="60" r="0.7"/>

    </g>


    <!-- HORIZON -->

    <ellipse
        cx="300"
        cy="280"
        rx="390"
        ry="60"
        fill="url(#glow)"/>


    <!-- HEADER -->

    <text
        x="30"
        y="30"
        font-family="Inter, system-ui, sans-serif"
        font-size="15"
        font-weight="700"
        fill="#c0caf5">

        Contribution Skyline

    </text>


    <text
        x="30"
        y="49"
        font-family="JetBrains Mono, monospace"
        font-size="9"
        fill="#bb9af7"
        letter-spacing="3">

        {current_year} · {USERNAME.upper()}

    </text>


    <!-- GROUND -->

    <polygon
        points="20,285 540,285 565,272 45,272"
        fill="#111522"
        opacity="0.85"/>

    <polygon
        points="20,285 540,285 565,272 45,272"
        fill="none"
        stroke="#292e42"
        stroke-width="0.7"/>


    <!-- ===================================== -->
    <!-- BACK ROW -->
    <!-- ===================================== -->
'''

    # BACK ROW
    for i in range(back_count):

        value = towers[i]

        level = tower_level(value, maximum)

        colors = tower_color(level)

        tower_height = calculate_height(value)

        x = chart_x + i * spacing + 8

        svg += tower_svg(
            x=x,
            base_y=255,
            width=tower_width,
            height=tower_height,
            depth=depth,
            colors=colors,
            glow=(level == "peak")
        )

    svg += """
    <!-- ===================================== -->
    <!-- FRONT ROW -->
    <!-- ===================================== -->
    """

    # FRONT ROW
    for i in range(front_count):

        index = back_count + i

        value = towers[index]

        level = tower_level(value, maximum)

        colors = tower_color(level)

        tower_height = calculate_height(value)

        x = chart_x + i * spacing

        svg += tower_svg(
            x=x,
            base_y=275,
            width=tower_width,
            height=tower_height,
            depth=depth,
            colors=colors,
            glow=(level == "peak")
        )

    # =========================================
    # SIDE PANEL
    # =========================================

    svg += f'''
    <line
        x1="570"
        y1="40"
        x2="570"
        y2="270"
        stroke="#292e42"
        stroke-width="0.7"/>


    <g
        transform="translate(600,65)"
        font-family="JetBrains Mono, monospace">

        <text
            font-size="9"
            fill="#bb9af7"
            letter-spacing="3">

            — ACTIVITY

        </text>


        <g transform="translate(0,25)">

            <rect
                width="10"
                height="10"
                fill="#7aa2f7"/>

            <text
                x="20"
                y="9"
                font-size="9"
                fill="#a9b1d6">

                low · activity

            </text>

        </g>


        <g transform="translate(0,45)">

            <rect
                width="10"
                height="10"
                fill="#7dcfff"/>

            <text
                x="20"
                y="9"
                font-size="9"
                fill="#a9b1d6">

                mid · activity

            </text>

        </g>


        <g transform="translate(0,65)">

            <rect
                width="10"
                height="10"
                fill="#bb9af7"/>

            <text
                x="20"
                y="9"
                font-size="9"
                fill="#a9b1d6">

                high · activity

            </text>

        </g>


        <g transform="translate(0,85)">

            <rect
                width="10"
                height="10"
                fill="#f7768e"/>

            <text
                x="20"
                y="9"
                font-size="9"
                fill="#a9b1d6">

                peak · activity

            </text>

        </g>


        <line
            x1="0"
            y1="110"
            x2="190"
            y2="110"
            stroke="#292e42"
            stroke-width="0.5"/>


        <text
            y="135"
            font-size="9"
            fill="#bb9af7"
            letter-spacing="3">

            — PROFILE

        </text>


        <text
            y="157"
            font-size="9"
            fill="#a9b1d6">

            contributions

        </text>

        <text
            x="190"
            y="157"
            text-anchor="end"
            font-size="11"
            fill="#7dcfff"
            font-weight="700">

            {total_contributions:,}

        </text>


        <text
            y="178"
            font-size="9"
            fill="#a9b1d6">

            active days

        </text>

        <text
            x="190"
            y="178"
            text-anchor="end"
            font-size="11"
            fill="#bb9af7"
            font-weight="700">

            {active_days}

        </text>


        <text
            y="199"
            font-size="9"
            fill="#a9b1d6">

            peak period

        </text>

        <text
            x="190"
            y="199"
            text-anchor="end"
            font-size="11"
            fill="#f7768e"
            font-weight="700">

            {peak_value}

        </text>


        <text
            y="220"
            font-size="9"
            fill="#a9b1d6">

            period

        </text>

        <text
            x="190"
            y="220"
            text-anchor="end"
            font-size="10"
            fill="#c0caf5"
            font-weight="700">

            180 DAYS

        </text>

    </g>


    <!-- FOOTER -->

    <text
        x="30"
        y="302"
        font-family="JetBrains Mono, monospace"
        font-size="8"
        letter-spacing="2"
        fill="#565f89">

        IARLEI-BARROS · CONTRIBUTION SKYLINE

    </text>


    <text
        x="870"
        y="302"
        text-anchor="end"
        font-family="JetBrains Mono, monospace"
        font-size="8"
        fill="#bb9af7"
        letter-spacing="2">

        TOKYO NIGHT

    </text>

</svg>
'''

    return svg


# ============================================================
# MAIN
# ============================================================

def main():
    print(f"Buscando contribuições de {USERNAME}...")

    days, total = get_contributions()

    print(f"Total de contribuições: {total}")
    print(f"Dias encontrados: {len(days)}")

    towers = create_towers(days)

    print("Valores das torres:")
    print(towers)

    svg = generate_svg(
        days=days,
        total_contributions=total,
        towers=towers
    )

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(svg)

    print(
        f"SVG atualizado com sucesso: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
