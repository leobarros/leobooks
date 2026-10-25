"""Gera as capturas do README/AppStream com a conta fictícia Mariana.

Uso:
    PLAYWRIGHT_BROWSERS_PATH=.playwright .venv/bin/python scripts/generate_screenshots.py

Os dados ficam em um diretório temporário; nenhum dado real é tocado.
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))
SHOTS = ROOT / "docs" / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

instance = Path(tempfile.mkdtemp(prefix="leobooks-mariana-"))
os.environ["LEOBOOKS_INSTANCE"] = str(instance)
os.environ["LEOBOOKS_SAMPLE_BOOK"] = "0"
os.environ["SECRET_KEY"] = "screenshots-only-secret"

from app import create_app  # noqa: E402
from models import BOOK_STATUSES, TAG_COLORS, Book, Note, Tag, User, db  # noqa: E402
from waitress import serve  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image  # noqa: E402

PORT = 5088
BASE = f"http://127.0.0.1:{PORT}"
PASSWORD = "leitura123"

application = create_app(
    {
        "TESTING": False,
        "WTF_CSRF_ENABLED": True,
        "SECRET_KEY": "screenshots-only-secret",
        "SAMPLE_BOOK_ENABLED": False,
        "COVER_LOOKUP_ENABLED": False,
        "SERVER_NAME": None,
    }
)


def seed() -> dict[str, str]:
    with application.app_context():
        db.create_all()
        user = User(
            name="Mariana Costa",
            email="mariana@leobooks.local",
            password_hash=generate_password_hash(PASSWORD),
            theme="light",
            is_admin=True,
            onboarding_completed=True,
        )
        db.session.add(user)
        db.session.flush()

        tag_names = [
            "política",
            "clássicos",
            "poder",
            "história",
            "literatura brasileira",
            "animais",
            "moral",
            "terra",
        ]
        tags = {}
        for index, name in enumerate(tag_names):
            tag = Tag(
                user_id=user.id,
                name=name,
                color_hex=TAG_COLORS[index % len(TAG_COLORS)],
            )
            db.session.add(tag)
            tags[name] = tag
        db.session.flush()

        now = datetime.now(timezone.utc)
        books = {}
        specs = [
            (
                "O Príncipe",
                "Nicolau Maquiavel",
                "PHYSICAL",
                128,
                74,
                0,
                "READING",
            ),
            (
                "A Revolução dos Bichos",
                "George Orwell",
                "DIGITAL",
                120,
                50,
                42,
                "READING",
            ),
            (
                "Torto Arado",
                "Itamar Vieira Junior",
                "PHYSICAL",
                264,
                264,
                0,
                "READ",
            ),
            (
                "A Arte da Guerra",
                "Sun Tzu",
                "PHYSICAL",
                128,
                0,
                0,
                "WANT_TO_READ",
            ),
            (
                "Memórias Póstumas de Brás Cubas",
                "Machado de Assis",
                "DIGITAL",
                208,
                208,
                100,
                "READ",
            ),
        ]
        for title, author, media, total, current, percent, status in specs:
            book = Book(
                user_id=user.id,
                title=title,
                authors=author,
                media_type=media,
                total_pages=total,
                current_page=current,
                percent_complete=percent,
                status=status,
            )
            db.session.add(book)
            books[title] = book
        db.session.flush()

        notes = [
            (
                "O Príncipe",
                "QUOTE",
                "O príncipe que depende inteiramente da fortuna cai quando ela muda; "
                "quem se apoia no próprio valor resiste.",
                "XXI",
                74,
                ["política", "clássicos", "poder"],
                now - timedelta(hours=2),
            ),
            (
                "O Príncipe",
                "SUMMARY",
                "Maquiavel separa a política da moral cristã e olha para o poder como "
                "ele é exercido, não como gostaríamos que fosse.",
                "XV",
                53,
                ["política", "poder"],
                now - timedelta(days=1, hours=3),
            ),
            (
                "O Príncipe",
                "INSIGHT",
                "A ideia de *virtù* ajuda a pensar em como a escola também precisa "
                "lidar com o que acontece, não só com o que deveria acontecer.",
                "VI",
                21,
                ["clássicos", "política"],
                now - timedelta(days=2),
            ),
            (
                "A Revolução dos Bichos",
                "QUOTE",
                "Todos os animais são iguais, mas alguns animais são mais iguais que outros.",
                "X",
                82,
                ["animais", "política"],
                now - timedelta(days=1),
            ),
            (
                "Torto Arado",
                "INSIGHT",
                "A terra não é cenário: é personagem. A escrita de Itamar faz o leitor "
                "sentir o peso da herança e do trabalho.",
                "Parte 2",
                168,
                ["literatura brasileira", "terra"],
                now - timedelta(days=3),
            ),
            (
                "Memórias Póstumas de Brás Cubas",
                "QUOTE",
                "Não tive filhos, não transmiti a nenhuma criatura o legado da nossa miséria.",
                "Cap. CLX",
                208,
                ["clássicos", "moral"],
                now - timedelta(days=4),
            ),
        ]
        for title, note_type, content, chapter, page_number, tag_names, created in notes:
            note = Note(
                user_id=user.id,
                book_id=books[title].id,
                type=note_type,
                content=content,
                chapter=chapter,
                page_number=page_number,
                created_at=created,
                updated_at=created,
            )
            note.tags = [tags[name] for name in tag_names]
            db.session.add(note)

        db.session.commit()
        return {
            "book_id": books["O Príncipe"].id,
            "user_id": user.id,
        }


def login(page) -> None:
    page.goto(f"{BASE}/login", wait_until="networkidle")
    page.fill("#loginEmail", "mariana@leobooks.local")
    page.fill("#loginPassword", PASSWORD)
    page.locator("button[type=submit]").first.click()
    page.wait_for_url(f"{BASE}/", wait_until="networkidle")
    page.wait_for_timeout(900)
    page.evaluate(
        "document.getElementById('lb-toasts')?.remove(); "
        "document.querySelectorAll('.lb-flash, .toast').forEach((el) => el.remove())"
    )
    page.wait_for_timeout(200)


def shot(page, name: str) -> None:
    page.evaluate(
        "document.getElementById('lb-toasts')?.remove(); "
        "document.querySelectorAll('.lb-flash, .toast').forEach((el) => el.remove())"
    )
    page.wait_for_timeout(150)
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=False, animations="disabled")
    with Image.open(SHOTS / f"{name}.png") as image:
        image.convert("RGB").save(SHOTS / f"{name}.webp", "WEBP", quality=88, method=6)
    print("captured", name)


def main() -> None:
    ids = seed()
    thread = threading.Thread(
        target=serve,
        args=(application,),
        kwargs={"host": "127.0.0.1", "port": PORT, "threads": 4},
        daemon=True,
    )
    thread.start()
    time.sleep(1)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        desktop = browser.new_context(
            viewport={"width": 1400, "height": 1000},
            device_scale_factor=1,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        page = desktop.new_page()
        login(page)
        shot(page, "inicio")

        page.goto(f"{BASE}/library", wait_until="networkidle")
        page.wait_for_timeout(500)
        shot(page, "biblioteca")

        page.goto(f"{BASE}/books/{ids['book_id']}", wait_until="networkidle")
        page.wait_for_timeout(500)
        shot(page, "livro")

        page.goto(f"{BASE}/", wait_until="networkidle")
        page.locator("[data-note-open]:visible").first.click()
        page.wait_for_selector("#noteModal.show")
        page.select_option("#noteBook", ids["book_id"])
        page.wait_for_timeout(500)
        shot(page, "nota")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        page.goto(f"{BASE}/books/new", wait_until="networkidle")
        page.wait_for_timeout(500)
        shot(page, "formato")
        desktop.close()

        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        mobile_page = mobile.new_page()
        login(mobile_page)
        shot(mobile_page, "mobile")
        mobile_page.locator("[data-note-open]:visible").first.click()
        mobile_page.wait_for_selector("#noteModal.show")
        mobile_page.wait_for_timeout(500)
        shot(mobile_page, "mobile-nota")
        mobile.close()

        # Tutorial: ativa novamente o onboarding só para a captura.
        with application.app_context():
            user = db.session.get(User, ids["user_id"])
            user.onboarding_completed = False
            db.session.commit()
        tutorial_context = browser.new_context(
            viewport={"width": 1400, "height": 1000},
            device_scale_factor=1,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        tutorial_page = tutorial_context.new_page()
        login(tutorial_page)
        tutorial_page.wait_for_selector(".lb-onboarding.show")
        tutorial_page.wait_for_timeout(500)
        shot(tutorial_page, "tutorial")
        tutorial_context.close()

        # Tema madrugada para a captura final.
        with application.app_context():
            user = db.session.get(User, ids["user_id"])
            user.onboarding_completed = True
            user.theme = "dark"
            db.session.commit()
        dark = browser.new_context(
            viewport={"width": 1400, "height": 1000},
            device_scale_factor=1,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        dark_page = dark.new_page()
        login(dark_page)
        shot(dark_page, "tema-escuro")
        dark.close()

        browser.close()

    # PNGs para AppStream/loja (sem perda adicional).
    for name in ("inicio", "biblioteca", "livro", "tema-escuro"):
        with Image.open(SHOTS / f"{name}.png") as image:
            image.convert("RGB").save(SHOTS / f"{name}.png", "PNG", optimize=True)
    print("done", instance)


if __name__ == "__main__":
    main()
