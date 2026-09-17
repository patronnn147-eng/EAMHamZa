from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.dirname(os.path.abspath(__file__))

SHOTS = [
    ("ss_pipeline_overview.png", "GitLab CI/CD Pipeline\n(overview — all stages)"),
    ("ss_pipeline_gitleaks.png", "GitLab CI Job\nscan-secrets (Gitleaks)"),
    ("ss_pipeline_sast.png", "GitLab CI Job\nsonarqube-scan (SAST)"),
    ("ss_pipeline_trivy.png", "GitLab CI Job\nimage-scan + iac-scan (Trivy)"),
    ("ss_pipeline_zap.png", "GitLab CI Job\ndast-scan (OWASP ZAP)"),
    ("ss_sonarqube_quality_gate.png", "SonarQube Quality Gate\n(project dashboard, 4/4 conditions)"),
]

W, H = 1600, 700

def make(name, label):
    img = Image.new("RGB", (W, H), (235, 237, 243))
    d = ImageDraw.Draw(img)
    # border
    d.rectangle([6, 6, W - 7, H - 7], outline=(150, 155, 175), width=4)
    # dashed inner frame effect (simple double rect)
    d.rectangle([24, 24, W - 25, H - 25], outline=(190, 195, 210), width=2)

    try:
        font_big = ImageFont.truetype("arial.ttf", 46)
        font_small = ImageFont.truetype("arial.ttf", 30)
    except Exception:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    title = "SCREENSHOT PLACEHOLDER"
    tb = d.textbbox((0, 0), title, font=font_big)
    d.text(((W - (tb[2]-tb[0])) / 2, H/2 - 130), title, fill=(90, 96, 120), font=font_big)

    lines = label.split("\n")
    y = H/2 - 30
    for line in lines:
        lb = d.textbbox((0, 0), line, font=font_small)
        d.text(((W - (lb[2]-lb[0])) / 2, y), line, fill=(40, 45, 65), font=font_small)
        y += 44

    footer = "Replace this file with the real GitLab pipeline screenshot (same filename)"
    fb = d.textbbox((0, 0), footer, font=font_small)
    d.text(((W - (fb[2]-fb[0])) / 2, H - 80), footer, fill=(120, 125, 145), font=font_small)

    img.save(os.path.join(OUT, name))
    print("wrote", name)

for name, label in SHOTS:
    make(name, label)
