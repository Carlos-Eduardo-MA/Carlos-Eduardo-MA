import html
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


USERNAME = os.environ.get("GITHUB_USERNAME", "Carlos-Eduardo-MA")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "assets" / "language-stats.svg"
API_ROOT = "https://api.github.com"
LANGUAGE_COLORS = ("#00f0ff", "#ff0055", "#00ff66", "#8b5cf6", "#f59e0b", "#38bdf8")

def get_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-profile-language-chart",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API returned HTTP {error.code} for {url}: {details}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Could not reach GitHub API for {url}: {error}") from error


def fetch_repositories():
    repositories = []
    page = 1
    while True:
        url = (
            f"{API_ROOT}/users/{quote(USERNAME, safe='')}/repos"
            f"?type=owner&visibility=public&per_page=100&page={page}"
        )
        page_repositories = get_json(url)
        if not isinstance(page_repositories, list):
            raise RuntimeError("GitHub API returned an unexpected repository list.")
        repositories.extend(page_repositories)
        if len(page_repositories) < 100:
            return repositories
        page += 1


def fetch_language_totals():
    totals = {}
    for repository in fetch_repositories():
        if repository.get("fork") or not repository.get("language"):
            continue

        owner = quote(USERNAME, safe="")
        name = quote(repository["name"], safe="")
        languages = get_json(f"{API_ROOT}/repos/{owner}/{name}/languages")
        if not isinstance(languages, dict):
            raise RuntimeError(
                f"GitHub API returned unexpected language data for {repository['name']}."
            )
        for language, byte_count in languages.items():
            if isinstance(byte_count, int) and byte_count > 0:
                totals[language] = totals.get(language, 0) + byte_count
    return totals


def render_svg(language_totals):
    ranked = sorted(language_totals.items(), key=lambda item: item[1], reverse=True)[:6]
    height = 88 + max(len(ranked), 1) * 42
    total_bytes = sum(language_totals.values())
    rows = []

    if not ranked:
        rows.append(
            '<text x="24" y="106" fill="#94a3b8" font-size="14">'
            "Nenhum repositório público com código detectado.</text>"
        )
    else:
        for index, (language, byte_count) in enumerate(ranked):
            y = 94 + index * 42
            percentage = byte_count / total_bytes * 100
            bar_width = 390 * percentage / 100
            color = LANGUAGE_COLORS[index % len(LANGUAGE_COLORS)]
            label = html.escape(language)
            rows.append(
                f'<text x="24" y="{y}" fill="#e2e8f0" font-size="13">'
                f"{label}</text>"
                f'<text x="654" y="{y}" fill="{color}" font-size="13" '
                f'text-anchor="end">{percentage:.1f}%</text>'
                f'<rect x="24" y="{y + 9}" width="390" height="7" rx="3.5" '
                'fill="#1e293b"/>'
                f'<rect x="24" y="{y + 9}" width="{bar_width:.2f}" height="7" '
                f'rx="3.5" fill="{color}"/>'
            )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="680" height="{height}" '
        f'viewBox="0 0 680 {height}" role="img">'
        "<title>Proporção de linguagens nos repositórios públicos</title>"
        '<rect width="680" height="100%" rx="14" fill="#05070f"/>'
        '<text x="24" y="34" fill="#00f0ff" font-family="Segoe UI, sans-serif" '
        'font-size="16" font-weight="700">LINGUAGENS POR VOLUME DE CÓDIGO</text>'
        '<text x="24" y="57" fill="#64748b" font-family="Segoe UI, sans-serif" '
        'font-size="10">REPOSITÓRIOS PÚBLICOS · ATÉ 6 LINGUAGENS</text>'
        + "".join(
            f'<g font-family="Segoe UI, sans-serif">{row}</g>' for row in rows
        )
        + "</svg>\n"
    )


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_svg(fetch_language_totals()), encoding="utf-8")
    print(f"Updated language chart: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
