import os
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter, QImage
from PySide6.QtCore import QSize, QByteArray

def generate_hand_asset(output_path: str):
    svg_code = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="500" height="500">
  <defs>
    <linearGradient id="skinGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FDE8DE" />
      <stop offset="45%" stop-color="#F6C6AE" />
      <stop offset="100%" stop-color="#E1A589" />
    </linearGradient>
    <linearGradient id="skinShadow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#D89271" />
      <stop offset="100%" stop-color="#B77353" />
    </linearGradient>
    <linearGradient id="penGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4B5563" />
      <stop offset="40%" stop-color="#1F2937" />
      <stop offset="100%" stop-color="#111827" />
    </linearGradient>
    <linearGradient id="silverGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#F3F4F6" />
      <stop offset="50%" stop-color="#9CA3AF" />
      <stop offset="100%" stop-color="#4B5563" />
    </linearGradient>
    <linearGradient id="sleeveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3B82F6" />
      <stop offset="100%" stop-color="#1E3A8A" />
    </linearGradient>
    <filter id="dropShad" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="6" dy="10" stdDeviation="8" flood-color="#000000" flood-opacity="0.30" />
    </filter>
  </defs>

  <g filter="url(#dropShad)">
    <!-- Marker Tip at (18, 18) -->
    <polygon points="18,18 44,28 28,44" fill="#0F172A" />
    <!-- Marker Collar -->
    <polygon points="44,28 66,48 48,66 28,44" fill="url(#silverGrad)" />
    <!-- Marker Body -->
    <polygon points="66,48 240,210 200,250 48,66" fill="url(#penGrad)" />
    <polygon points="100,80 115,95 98,112 83,97" fill="#38BDF8" />

    <!-- Back fingers (Little and Ring finger) -->
    <path d="M 230,220 C 270,250 250,290 210,270 Z" fill="url(#skinShadow)" stroke="#A06346" stroke-width="2" />
    <path d="M 190,190 C 240,230 220,265 180,240 Z" fill="url(#skinShadow)" stroke="#A06346" stroke-width="2" />

    <!-- Middle finger -->
    <path d="M 150,150 C 200,190 190,230 145,200 Z" fill="url(#skinShadow)" stroke="#A06346" stroke-width="2" />

    <!-- Hand Palm base -->
    <path d="M 140,190 C 200,240 280,280 380,360 L 320,430 C 220,350 140,270 100,200 Z" fill="url(#skinGrad)" />

    <!-- Thumb (holding side of pen) -->
    <path d="M 65,95 C 75,75 110,90 120,115 C 135,145 130,175 95,160 C 70,150 55,115 65,95 Z" fill="url(#skinGrad)" stroke="#A06346" stroke-width="2" />
    <!-- Thumb nail -->
    <ellipse cx="85" cy="96" rx="9" ry="6" transform="rotate(35 85 96)" fill="#FFFFFF" fill-opacity="0.65" />

    <!-- Index Finger (wrapped elegantly on top of marker) -->
    <path d="M 85,55 C 115,45 145,60 160,85 C 180,115 175,145 140,140 C 115,135 90,105 85,55 Z" fill="url(#skinGrad)" stroke="#A06346" stroke-width="2" />
    <!-- Index nail -->
    <ellipse cx="108" cy="62" rx="10" ry="7" transform="rotate(25 108 62)" fill="#FFFFFF" fill-opacity="0.65" />

    <!-- Sleeve Cuff coming from bottom-right -->
    <path d="M 320,310 C 370,350 420,390 490,440 L 440,500 C 370,450 310,390 270,360 Z" fill="url(#sleeveGrad)" stroke="#1E3A8A" stroke-width="2" />
    <path d="M 270,360 L 320,310 L 335,325 L 285,375 Z" fill="#FFFFFF" opacity="0.85" />
  </g>
</svg>"""

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    renderer = QSvgRenderer(QByteArray(svg_code.encode("utf-8")))
    img = QImage(QSize(600, 600), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()

    img.save(output_path)
    print(f"Generated clean vector hand graphic: {output_path}")

if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "d:/project_pos/tools/tools-ai-animation/assets/hand_drawing.png"
    generate_hand_asset(out)
