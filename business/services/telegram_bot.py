"""
Telegram Bot handler service.
Business Logic: §27 (Notifications), §37 (Telegram Bot)

Processes incoming Telegram webhook updates:
- Commands: /start, /status, /help, /stop, /defect, /actual, /split, /glaze, /recipe, /plan, /photo
- Photos: receive from masters, store with position linking
- Callback queries: inline button presses
"""

import logging
import time
import uuid as _uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from api.config import get_settings
from api.models import (
    User, Task, OrderPosition, ProductionOrder,
    Factory, UserFactory, PositionPhoto,
    Recipe, RecipeMaterial, RecipeKilnConfig, Material,
    Batch, Resource, DailyTaskDistribution,
    MaterialTransaction, MaterialStock, MaterialPurchaseRequest,
)
from api.enums import (
    TaskStatus, PositionStatus, ResourceType, BatchStatus,
    TransactionType, PurchaseStatus,
)

logger = logging.getLogger("moonjar.telegram_bot")

TELEGRAM_API = "https://api.telegram.org/bot{token}"

# ────────────────────────────────────────────────────────────────
# Multilingual message templates (en / id / ru)
# ────────────────────────────────────────────────────────────────

MESSAGES: dict[str, dict[str, str]] = {
    # ── Account linking ───────────────────────────────────────────
    "account_not_linked": {
        "en": "Account not linked. Type /start to link.",
        "id": "Akun belum terhubung. Ketik /start untuk menghubungkan.",
        "ru": "Аккаунт не привязан. Введите /start для привязки.",
    },
    "account_already_linked": {
        "en": "Your account is already linked as *{name}* ({email}).\nType /stop to unlink.",
        "id": "Akun Anda sudah terhubung sebagai *{name}* ({email}).\nKetik /stop untuk memutuskan koneksi.",
        "ru": "Ваш аккаунт привязан как *{name}* ({email}).\nВведите /stop для отвязки.",
    },
    "welcome_start": {
        "en": "Welcome to *Moonjar PMS*, {first_name}!\n\nTo link your Telegram account, please send the email registered in PMS.",
        "id": "Selamat datang di *Moonjar PMS*, {first_name}!\n\nUntuk menghubungkan akun Telegram Anda, silakan kirim email yang terdaftar di sistem PMS.",
        "ru": "Добро пожаловать в *Moonjar PMS*, {first_name}!\n\nДля привязки Telegram-аккаунта отправьте email, зарегистрированный в PMS.",
    },
    "group_welcome": {
        "en": "Moonjar PMS Bot is active in this group.\nSend photos for production documentation.\nType /help for commands.",
        "id": "Moonjar PMS Bot aktif di grup ini.\nKirim foto untuk dokumentasi produksi.\nKetik /help untuk daftar perintah.",
        "ru": "Moonjar PMS Bot активен в этой группе.\nОтправляйте фото для документации производства.\nВведите /help для списка команд.",
    },
    "send_email_prompt": {
        "en": "Please send the email registered in Moonjar PMS to link your account.",
        "id": "Silakan kirim email yang terdaftar di Moonjar PMS untuk menghubungkan akun.",
        "ru": "Отправьте email, зарегистрированный в Moonjar PMS, для привязки аккаунта.",
    },
    "email_not_found": {
        "en": "Email not found in the system.",
        "id": "Email tidak ditemukan di sistem.",
        "ru": "Email не найден в системе.",
    },
    "already_linked_other": {
        "en": "This PMS account is already linked to another Telegram account.\nContact your administrator for help.",
        "id": "Akun PMS ini sudah terhubung ke akun Telegram lain.\nHubungi administrator untuk bantuan.",
        "ru": "Этот аккаунт PMS уже привязан к другому Telegram-аккаунту.\nОбратитесь к администратору.",
    },
    "link_success": {
        "en": "Linked! Your Telegram is now connected to *{name}* ({email}).\n\nYou will receive production notifications here.\nType /status to see your tasks.",
        "id": "Terhubung! Akun Telegram Anda sekarang terhubung ke *{name}* ({email}).\n\nAnda akan menerima notifikasi produksi di sini.\nKetik /status untuk melihat tugas Anda.",
        "ru": "Привязано! Ваш Telegram подключён к *{name}* ({email}).\n\nВы будете получать уведомления о производстве здесь.\nВведите /status для просмотра задач.",
    },
    "account_unlinked": {
        "en": "Your Telegram account has been unlinked from Moonjar PMS.\nType /start to reconnect.",
        "id": "Akun Telegram Anda telah diputuskan dari Moonjar PMS.\nKetik /start untuk menghubungkan kembali.",
        "ru": "Ваш Telegram отвязан от Moonjar PMS.\nВведите /start для повторной привязки.",
    },
    "account_not_connected": {
        "en": "Account not connected.",
        "id": "Akun tidak terhubung.",
        "ru": "Аккаунт не подключён.",
    },
    "already_linked_msg": {
        "en": "Account already linked as *{name}*.\nType /help for commands.",
        "id": "Akun sudah terhubung sebagai *{name}*.\nKetik /help untuk daftar perintah.",
        "ru": "Аккаунт привязан как *{name}*.\nВведите /help для списка команд.",
    },
    # ── Commands ──────────────────────────────────────────────────
    "unknown_command": {
        "en": "Unknown command. Type /help for available commands.",
        "id": "Perintah tidak dikenal. Ketik /help untuk daftar perintah.",
        "ru": "Неизвестная команда. Введите /help для списка команд.",
    },
    "no_pending_tasks": {
        "en": "No pending tasks.",
        "id": "Tidak ada tugas yang tertunda.",
        "ru": "Нет ожидающих задач.",
    },
    "your_tasks": {
        "en": "Your tasks:",
        "id": "Tugas Anda:",
        "ru": "Ваши задачи:",
    },
    "help_text": {
        "en": (
            "*Moonjar PMS Bot*\n\n"
            "Available commands:\n"
            "/start — Link Telegram account\n"
            "/status — View pending tasks\n"
            "/defect <pos\\_id> <percent> — Report defect\n"
            "/actual <pos\\_id> <quantity> — Record actual output\n"
            "/split <pos\\_id> <qty1> <qty2> ... — Split position\n"
            "/glaze <pos\\_id> — Position glaze info\n"
            "/recipe <collection> <color> [size] — Search recipe\n"
            "/plan — Tomorrow's production plan\n"
            "/photo — Send photo for documentation\n"
            "/help — Show this help\n"
            "/stop — Unlink account\n\n"
            "Send photos in group for production documentation."
        ),
        "id": (
            "*Moonjar PMS Bot*\n\n"
            "Perintah yang tersedia:\n"
            "/start — Hubungkan akun Telegram\n"
            "/status — Lihat tugas yang tertunda\n"
            "/defect <pos\\_id> <persen> — Lapor defect\n"
            "/actual <pos\\_id> <jumlah> — Catat output aktual\n"
            "/split <pos\\_id> <qty1> <qty2> ... — Bagi posisi\n"
            "/glaze <pos\\_id> — Info glasir posisi\n"
            "/recipe <koleksi> <warna> [ukuran] — Cari resep\n"
            "/plan — Rencana produksi besok\n"
            "/photo — Kirim foto untuk dokumentasi\n"
            "/help — Tampilkan bantuan ini\n"
            "/stop — Putuskan koneksi akun\n\n"
            "Kirim foto di grup untuk dokumentasi produksi."
        ),
        "ru": (
            "*Moonjar PMS Bot*\n\n"
            "Доступные команды:\n"
            "/start — Привязать аккаунт Telegram\n"
            "/status — Просмотреть задачи\n"
            "/defect <pos\\_id> <процент> — Сообщить о дефекте\n"
            "/actual <pos\\_id> <кол-во> — Записать фактический выход\n"
            "/split <pos\\_id> <qty1> <qty2> ... — Разделить позицию\n"
            "/glaze <pos\\_id> — Информация о глазури\n"
            "/recipe <коллекция> <цвет> [размер] — Поиск рецепта\n"
            "/plan — Производственный план на завтра\n"
            "/photo — Отправить фото\n"
            "/help — Показать справку\n"
            "/stop — Отвязать аккаунт\n\n"
            "Отправляйте фото в группе для документации."
        ),
    },
    # ── Photo & delivery ──────────────────────────────────────────
    "photo_received": {
        "en": "Photo received ({type_label}).",
        "id": "Foto diterima ({type_label}).",
        "ru": "Фото получено ({type_label}).",
    },
    "photo_linked": {
        "en": " Linked to position {pos_label}.",
        "id": " Terhubung ke posisi {pos_label}.",
        "ru": " Привязано к позиции {pos_label}.",
    },
    "photo_instructions": {
        "en": (
            "*Send Production Photo*\n\n"
            "Send a photo directly in this chat (no /photo command needed).\n\n"
            "Add a caption to tag:\n"
            "- Position number (e.g. #123)\n"
            "- Type: glaze, fire, defect, pack\n\n"
            "Example: send a photo with caption `#123 glaze`"
        ),
        "id": (
            "*Kirim Foto Produksi*\n\n"
            "Kirim foto langsung di chat ini (tanpa perintah /photo).\n\n"
            "Tambahkan caption untuk menandai:\n"
            "- Nomor posisi (contoh: #123)\n"
            "- Tipe: glasir, bakar, defect, kemas\n\n"
            "Contoh: kirim foto dengan caption `#123 glasir`"
        ),
        "ru": (
            "*Отправить фото производства*\n\n"
            "Отправьте фото прямо в этот чат (без команды /photo).\n\n"
            "Добавьте подпись:\n"
            "- Номер позиции (напр. #123)\n"
            "- Тип: глазурь, обжиг, дефект, упаковка\n\n"
            "Пример: фото с подписью `#123 глазурь`"
        ),
    },
    "cannot_determine_factory": {
        "en": "Cannot determine factory for this photo.",
        "id": "Tidak dapat menentukan pabrik untuk foto ini.",
        "ru": "Не удалось определить фабрику для этого фото.",
    },
    "delivery_photo_failed": {
        "en": "Failed to process delivery photo. Photo is saved.",
        "id": "Gagal memproses foto pengiriman. Foto tetap tersimpan.",
        "ru": "Не удалось обработать фото доставки. Фото сохранено.",
    },
    "delivery_server_error": {
        "en": "Failed to contact server to process photo. Try again later.",
        "id": "Gagal menghubungi server untuk memproses foto. Coba lagi nanti.",
        "ru": "Не удалось связаться с сервером для обработки фото. Попробуйте позже.",
    },
    "delivery_process_error": {
        "en": "Failed to process delivery photo. Please try again or input manually.",
        "id": "Gagal memproses foto pengiriman. Silakan coba lagi atau input secara manual.",
        "ru": "Не удалось обработать фото доставки. Попробуйте снова или введите вручную.",
    },
    "delivery_no_items": {
        "en": "Delivery photo received, but no material list found. Please input receipt manually.",
        "id": "Foto pengiriman diterima, tetapi tidak ditemukan daftar material. Silakan input penerimaan secara manual.",
        "ru": "Фото доставки получено, но список материалов не найден. Введите приёмку вручную.",
    },
    "delivery_header": {
        "en": "\U0001f4e6 Material Receipt — {supplier}",
        "id": "\U0001f4e6 Penerimaan Material — {supplier}",
        "ru": "\U0001f4e6 Приёмка материалов — {supplier}",
    },
    "delivery_ref": {
        "en": "\U0001f4cb Ref: {ref} | Date: {date}",
        "id": "\U0001f4cb Ref: {ref} | Tanggal: {date}",
        "ru": "\U0001f4cb Ссылка: {ref} | Дата: {date}",
    },
    "found_items": {
        "en": "Found {count} items:",
        "id": "Ditemukan {count} item:",
        "ru": "Найдено {count} позиций:",
    },
    "not_found_label": {
        "en": "NOT FOUND",
        "id": "TIDAK DITEMUKAN",
        "ru": "НЕ НАЙДЕНО",
    },
    "suggestion_label": {
        "en": "\U0001f4a1 Suggestion: {name}",
        "id": "\U0001f4a1 Saran: {name}",
        "ru": "\U0001f4a1 Предложение: {name}",
    },
    "unknown_supplier": {
        "en": "Unknown",
        "id": "Tidak diketahui",
        "ru": "Неизвестно",
    },
    "confirm_receipt_btn": {
        "en": "\u2705 Confirm Receipt",
        "id": "\u2705 Konfirmasi Penerimaan",
        "ru": "\u2705 Подтвердить приёмку",
    },
    "edit_items_btn": {
        "en": "\u270f\ufe0f Edit Items",
        "id": "\u270f\ufe0f Edit Items",
        "ru": "\u270f\ufe0f Редактировать",
    },
    "cancel_btn": {
        "en": "\u274c Cancel",
        "id": "\u274c Batal",
        "ru": "\u274c Отмена",
    },
    "create_new_btn": {
        "en": "\u2795 Create New",
        "id": "\u2795 Buat Baru",
        "ru": "\u2795 Создать новый",
    },
    "material_not_found_prompt": {
        "en": "\u26a0\ufe0f Material not found: \"{name}\"\n",
        "id": "\u26a0\ufe0f Material tidak ditemukan: \"{name}\"\n",
        "ru": "\u26a0\ufe0f Материал не найден: \"{name}\"\n",
    },
    "standard_name_hint": {
        "en": "\U0001f4a1 Standard name: {name}\n",
        "id": "\U0001f4a1 Nama standar: {name}\n",
        "ru": "\U0001f4a1 Стандартное имя: {name}\n",
    },
    "choose_or_create": {
        "en": "Choose matching material or create new:",
        "id": "Pilih material yang sesuai atau tambah baru:",
        "ru": "Выберите материал или создайте новый:",
    },
    # ── Delivery confirmation ─────────────────────────────────────
    "receipt_expired": {
        "en": "This receipt has expired (>30 min) or already processed.",
        "id": "Penerimaan ini sudah kedaluwarsa (>30 menit) atau sudah diproses.",
        "ru": "Приёмка истекла (>30 мин) или уже обработана.",
    },
    "receipt_cancelled": {
        "en": "\u274c Receipt cancelled.",
        "id": "\u274c Penerimaan dibatalkan.",
        "ru": "\u274c Приёмка отменена.",
    },
    "item_not_found": {
        "en": "Item not found.",
        "id": "Item tidak ditemukan.",
        "ru": "Позиция не найдена.",
    },
    "material_not_found": {
        "en": "Material not found.",
        "id": "Material tidak ditemukan.",
        "ru": "Материал не найден.",
    },
    "mapped_to": {
        "en": "\u2705 \"{original}\" mapped to *{material}*",
        "id": "\u2705 \"{original}\" dipetakan ke *{material}*",
        "ru": "\u2705 \"{original}\" сопоставлено с *{material}*",
    },
    "new_material_created": {
        "en": "\u2795 New material created: *{name}*\n\"{original}\" mapped to this new material.",
        "id": "\u2795 Material baru dibuat: *{name}*\n\"{original}\" dipetakan ke material baru ini.",
        "ru": "\u2795 Новый материал создан: *{name}*\n\"{original}\" сопоставлено с новым материалом.",
    },
    "failed_create_material": {
        "en": "Failed to create new material: {error}",
        "id": "Gagal membuat material baru: {error}",
        "ru": "Не удалось создать материал: {error}",
    },
    "unmatched_items_warning": {
        "en": "\u26a0\ufe0f There are still unmapped items: {names}\nMap them first or cancel the receipt.",
        "id": "\u26a0\ufe0f Masih ada item yang belum dipetakan: {names}\nPetakan terlebih dahulu atau batalkan penerimaan.",
        "ru": "\u26a0\ufe0f Есть несопоставленные позиции: {names}\nСопоставьте их или отмените приёмку.",
    },
    "still_unmatched": {
        "en": "There are still unmapped items!",
        "id": "Masih ada item belum dipetakan!",
        "ru": "Есть несопоставленные позиции!",
    },
    "receipt_confirmed_header": {
        "en": "\u2705 Receipt Confirmed — {supplier}",
        "id": "\u2705 Penerimaan Dikonfirmasi — {supplier}",
        "ru": "\u2705 Приёмка подтверждена — {supplier}",
    },
    "receipt_total": {
        "en": "Total: {count} materials received and stock updated.",
        "id": "Total: {count} material diterima dan stok diperbarui.",
        "ru": "Итого: {count} материалов принято, остатки обновлены.",
    },
    "receipt_save_failed": {
        "en": "Failed to save receipt transactions: {error}\nPlease try again or input manually.",
        "id": "Gagal menyimpan transaksi penerimaan: {error}\nSilakan coba lagi atau input secara manual.",
        "ru": "Не удалось сохранить транзакции: {error}\nПопробуйте снова или введите вручную.",
    },
    # ── Edit flow ─────────────────────────────────────────────────
    "edit_mode_active": {
        "en": "\u270f\ufe0f Edit mode active — {count} items.\nEdit one by one or press Finish Edit anytime.",
        "id": "\u270f\ufe0f Mode edit aktif — {count} item.\nEdit satu per satu atau tekan Selesai Edit kapan saja.",
        "ru": "\u270f\ufe0f Режим редактирования — {count} позиций.\nРедактируйте по одной или нажмите Завершить.",
    },
    "search_db_btn": {
        "en": "\U0001f50d Search DB",
        "id": "\U0001f50d Cari di DB",
        "ru": "\U0001f50d Поиск в БД",
    },
    "change_qty_btn": {
        "en": "\u270f\ufe0f Change Qty",
        "id": "\u270f\ufe0f Ubah Qty",
        "ru": "\u270f\ufe0f Изменить кол-во",
    },
    "skip_btn": {
        "en": "\u23ed Skip",
        "id": "\u23ed Lewati",
        "ru": "\u23ed Пропустить",
    },
    "finish_edit_btn": {
        "en": "\u2705 Finish Edit",
        "id": "\u2705 Selesai Edit",
        "ru": "\u2705 Завершить",
    },
    "choose_action": {
        "en": "Choose action:",
        "id": "Pilih aksi:",
        "ru": "Выберите действие:",
    },
    "quantity_label": {
        "en": "Quantity: {qty} {unit}",
        "id": "Jumlah: {qty} {unit}",
        "ru": "Кол-во: {qty} {unit}",
    },
    "enter_valid_number": {
        "en": "Enter a valid number (e.g. 500):",
        "id": "Masukkan angka yang valid (contoh: 500):",
        "ru": "Введите число (напр. 500):",
    },
    "qty_changed": {
        "en": "\u2705 Quantity changed: {name} — {qty} {unit}",
        "id": "\u2705 Jumlah diubah: {name} — {qty} {unit}",
        "ru": "\u2705 Количество изменено: {name} — {qty} {unit}",
    },
    "enter_material_name": {
        "en": "Enter the material name:",
        "id": "Masukkan nama material:",
        "ru": "Введите название материала:",
    },
    "choose_material_type": {
        "en": "Material: {name}\nChoose material type:",
        "id": "Material: {name}\nPilih tipe material:",
        "ru": "Материал: {name}\nВыберите тип материала:",
    },
    "no_materials_found": {
        "en": "No materials found for \"{name}\".\nUse \"\u2795 Create New\" to add a new material.",
        "id": "Tidak ada material ditemukan untuk \"{name}\".\nGunakan \"\u2795 Buat Baru\" untuk membuat material baru.",
        "ru": "Материалы не найдены для \"{name}\".\nИспользуйте \"\u2795 Создать новый\".",
    },
    "matching_materials": {
        "en": "\U0001f50d Matching materials for \"{name}\":",
        "id": "\U0001f50d Material cocok untuk \"{name}\":",
        "ru": "\U0001f50d Подходящие материалы для \"{name}\":",
    },
    "back_btn": {
        "en": "\u2b05 Back",
        "id": "\u2b05 Kembali",
        "ru": "\u2b05 Назад",
    },
    "enter_material_name_en": {
        "en": "Enter material name (EN) for \"{name}\":",
        "id": "Masukkan nama material (EN) untuk \"{name}\":",
        "ru": "Введите название материала (EN) для \"{name}\":",
    },
    "choose_subtype": {
        "en": "Material: {name}\nType: {type}\nChoose subtype:",
        "id": "Material: {name}\nTipe: {type}\nPilih subtipe:",
        "ru": "Материал: {name}\nТип: {type}\nВыберите подтип:",
    },
    "edited_header": {
        "en": "\U0001f4e6 Material Receipt (EDITED) — {supplier}",
        "id": "\U0001f4e6 Penerimaan Material (DIEDIT) — {supplier}",
        "ru": "\U0001f4e6 Приёмка материалов (ИЗМЕНЕНО) — {supplier}",
    },
    "items_skipped": {
        "en": "\u23ed {count} items skipped (will not be received)",
        "id": "\u23ed {count} item dilewati (tidak akan diterima)",
        "ru": "\u23ed {count} позиций пропущено (не будут приняты)",
    },
    # ── Defect / actual / split ───────────────────────────────────
    "defect_format": {
        "en": "Format: /defect <pos\\_id> <percent>\nExample: /defect 12345 8",
        "id": "Format: /defect <pos\\_id> <persen>\nContoh: /defect 12345 8",
        "ru": "Формат: /defect <pos\\_id> <процент>\nПример: /defect 12345 8",
    },
    "defect_must_be_number": {
        "en": "Defect percent must be a number. Example: /defect 12345 8",
        "id": "Persen defect harus berupa angka. Contoh: /defect 12345 8",
        "ru": "Процент дефекта должен быть числом. Пример: /defect 12345 8",
    },
    "position_not_found": {
        "en": "Position '{pos}' not found.",
        "id": "Posisi '{pos}' tidak ditemukan.",
        "ru": "Позиция '{pos}' не найдена.",
    },
    "defect_recorded": {
        "en": "Defect recorded: {pct}% for position {pos}. Target: {target}%.",
        "id": "Defect dicatat: {pct}% untuk posisi {pos}. Target: {target}%.",
        "ru": "Дефект записан: {pct}% для позиции {pos}. Цель: {target}%.",
    },
    "defect_exceeded": {
        "en": "\n\u26a0\ufe0f Threshold exceeded — 5-Why task created.",
        "id": "\n\u26a0\ufe0f Batas terlampaui — tugas 5-Why dibuat.",
        "ru": "\n\u26a0\ufe0f Порог превышен — создана задача 5-Why.",
    },
    "defect_record_failed": {
        "en": "Failed to record defect: {error}",
        "id": "Gagal mencatat defect: {error}",
        "ru": "Не удалось записать дефект: {error}",
    },
    "actual_format": {
        "en": "Format: /actual <pos\\_id> <quantity>\nExample: /actual 12345 95",
        "id": "Format: /actual <pos\\_id> <jumlah>\nContoh: /actual 12345 95",
        "ru": "Формат: /actual <pos\\_id> <кол-во>\nПример: /actual 12345 95",
    },
    "actual_must_be_int": {
        "en": "Quantity must be a whole number. Example: /actual 12345 95",
        "id": "Jumlah harus berupa angka bulat. Contoh: /actual 12345 95",
        "ru": "Количество должно быть целым числом. Пример: /actual 12345 95",
    },
    "actual_recorded": {
        "en": "Output recorded: {actual} pcs for {pos} (planned: {planned})",
        "id": "Output dicatat: {actual} pcs untuk {pos} (rencana: {planned})",
        "ru": "Выход записан: {actual} шт для {pos} (план: {planned})",
    },
    "actual_deficit": {
        "en": "\n\u26a0\ufe0f {diff} pcs below plan.",
        "id": "\n\u26a0\ufe0f Kurang {diff} pcs dari rencana.",
        "ru": "\n\u26a0\ufe0f Не хватает {diff} шт до плана.",
    },
    "actual_record_failed": {
        "en": "Failed to record output: {error}",
        "id": "Gagal mencatat output: {error}",
        "ru": "Не удалось записать выход: {error}",
    },
    "split_format": {
        "en": "Format: /split <pos\\_id> <qty1> <qty2> [qty3...]\nExample: /split 12345 50 30 20",
        "id": "Format: /split <pos\\_id> <qty1> <qty2> [qty3...]\nContoh: /split 12345 50 30 20",
        "ru": "Формат: /split <pos\\_id> <qty1> <qty2> [qty3...]\nПример: /split 12345 50 30 20",
    },
    "all_must_be_int": {
        "en": "All quantities must be whole numbers.",
        "id": "Semua jumlah harus berupa angka bulat.",
        "ru": "Все количества должны быть целыми числами.",
    },
    "min_2_parts": {
        "en": "At least 2 parts required to split a position.",
        "id": "Minimal 2 bagian untuk membagi posisi.",
        "ru": "Нужно минимум 2 части для разделения позиции.",
    },
    "cannot_split": {
        "en": "Cannot split position: {reason}",
        "id": "Tidak bisa membagi posisi: {reason}",
        "ru": "Невозможно разделить позицию: {reason}",
    },
    "split_total_mismatch": {
        "en": "Total of parts ({total}) must equal position quantity ({qty}).",
        "id": "Total bagian ({total}) harus sama dengan jumlah posisi ({qty}).",
        "ru": "Сумма частей ({total}) должна равняться количеству позиции ({qty}).",
    },
    "split_success": {
        "en": "Position split: {pos} -> {children}",
        "id": "Posisi dibagi: {pos} -> {children}",
        "ru": "Позиция разделена: {pos} -> {children}",
    },
    "split_failed": {
        "en": "Failed to split position: {error}",
        "id": "Gagal membagi posisi: {error}",
        "ru": "Не удалось разделить позицию: {error}",
    },
    # ── Glaze / recipe / plan ─────────────────────────────────────
    "glaze_format": {
        "en": "Format: /glaze <pos\\_id>\nExample: /glaze 12345",
        "id": "Format: /glaze <pos\\_id>\nContoh: /glaze 12345",
        "ru": "Формат: /glaze <pos\\_id>\nПример: /glaze 12345",
    },
    "glaze_info_header": {
        "en": "*Glaze Info — {pos}*\n",
        "id": "*Info Glasir — {pos}*\n",
        "ru": "*Информация о глазури — {pos}*\n",
    },
    "recipe_label": {
        "en": "Recipe: {name}",
        "id": "Resep: {name}",
        "ru": "Рецепт: {name}",
    },
    "type_label": {
        "en": "Type: {type}",
        "id": "Tipe: {type}",
        "ru": "Тип: {type}",
    },
    "temperature_label": {
        "en": "Temp: {temp} C",
        "id": "Suhu: {temp} C",
        "ru": "Темп: {temp} C",
    },
    "duration_label": {
        "en": "Duration: {hours} h",
        "id": "Durasi: {hours} jam",
        "ru": "Длительность: {hours} ч",
    },
    "two_stage_yes": {
        "en": "2-stage firing: Yes",
        "id": "Pembakaran 2 tahap: Ya",
        "ru": "2-этапный обжиг: Да",
    },
    "materials_label": {
        "en": "\nMaterials:",
        "id": "\nBahan:",
        "ru": "\nМатериалы:",
    },
    "recipe_not_found": {
        "en": "Recipe: not found",
        "id": "Resep: tidak ditemukan",
        "ru": "Рецепт: не найден",
    },
    "recipe_not_set": {
        "en": "Recipe: not set",
        "id": "Resep: belum ditentukan",
        "ru": "Рецепт: не назначен",
    },
    "color_label": {
        "en": "\nColor: {color}",
        "id": "\nWarna: {color}",
        "ru": "\nЦвет: {color}",
    },
    "color_2_label": {
        "en": "Color 2: {color}",
        "id": "Warna 2: {color}",
        "ru": "Цвет 2: {color}",
    },
    "size_label": {
        "en": "Size: {size}",
        "id": "Ukuran: {size}",
        "ru": "Размер: {size}",
    },
    "qty_pcs": {
        "en": "Quantity: {qty} pcs",
        "id": "Jumlah: {qty} pcs",
        "ru": "Кол-во: {qty} шт",
    },
    "glaze_schedule": {
        "en": "Glaze schedule: {date}",
        "id": "Jadwal glasir: {date}",
        "ru": "Расписание глазури: {date}",
    },
    "two_stage_type": {
        "en": "2-stage: Yes ({type})",
        "id": "2-tahap: Ya ({type})",
        "ru": "2-этапный: Да ({type})",
    },
    "recipe_search_format": {
        "en": "Format: /recipe <collection> <color> [size]\nExample: /recipe Classic White 30x60",
        "id": "Format: /recipe <koleksi> <warna> [ukuran]\nContoh: /recipe Classic White 30x60",
        "ru": "Формат: /recipe <коллекция> <цвет> [размер]\nПример: /recipe Classic White 30x60",
    },
    "recipe_min_args": {
        "en": "Minimum: /recipe <collection> <color>",
        "id": "Minimal: /recipe <koleksi> <warna>",
        "ru": "Минимум: /recipe <коллекция> <цвет>",
    },
    "recipe_search_not_found": {
        "en": "Recipe not found for '{query}'.",
        "id": "Resep tidak ditemukan untuk '{query}'.",
        "ru": "Рецепт не найден для '{query}'.",
    },
    "collection_label": {
        "en": "Collection: {name}",
        "id": "Koleksi: {name}",
        "ru": "Коллекция: {name}",
    },
    "plan_header": {
        "en": "*Production Plan {date} — {factory}*\n",
        "id": "*Rencana Produksi {date} — {factory}*\n",
        "ru": "*План производства {date} — {factory}*\n",
    },
    "glaze_section": {
        "en": "*Glazing: {count} positions*",
        "id": "*Glasir: {count} posisi*",
        "ru": "*Глазурь: {count} позиций*",
    },
    "kiln_section": {
        "en": "\n*Kiln: {count} positions*",
        "id": "\n*Kiln: {count} posisi*",
        "ru": "\n*Обжиг: {count} позиций*",
    },
    "kiln_batch_section": {
        "en": "\n*Kiln: {count} batches*",
        "id": "\n*Kiln: {count} batch*",
        "ru": "\n*Обжиг: {count} партий*",
    },
    "sorting_section": {
        "en": "\n*Sorting: {count} positions*",
        "id": "\n*Sortir: {count} posisi*",
        "ru": "\n*Сортировка: {count} позиций*",
    },
    "no_plan_tomorrow": {
        "en": "No production plan for tomorrow.",
        "id": "Tidak ada rencana produksi untuk besok.",
        "ru": "Нет производственного плана на завтра.",
    },
    "factory_not_found": {
        "en": "Factory not found.",
        "id": "Pabrik tidak ditemukan.",
        "ru": "Фабрика не найдена.",
    },
    "not_assigned_factory": {
        "en": "You are not assigned to any factory.",
        "id": "Anda belum terdaftar di pabrik manapun.",
        "ru": "Вы не привязаны ни к одной фабрике.",
    },
    # ── Misc ──────────────────────────────────────────────────────
    "receipt_expired_short": {
        "en": "Receipt expired.",
        "id": "Penerimaan sudah kedaluwarsa.",
        "ru": "Приёмка истекла.",
    },
    "data_invalid": {
        "en": "Data invalid",
        "id": "Data tidak valid",
        "ru": "Данные недействительны",
    },
    "edit_session_not_found": {
        "en": "Edit session not found. Press Edit Items again.",
        "id": "Sesi edit tidak ditemukan. Tekan Edit Items lagi.",
        "ru": "Сессия редактирования не найдена. Нажмите Edit Items снова.",
    },
    "error_occurred": {
        "en": "An error occurred",
        "id": "Terjadi kesalahan",
        "ru": "Произошла ошибка",
    },
}

# Default language for group chats or unlinked users
_DEFAULT_LANG = "id"


def get_user_language(db: Session, telegram_user_id: Optional[int] = None, chat_id: Optional[int] = None) -> str:
    """
    Determine user language from their PMS profile.
    Falls back to factory telegram_language, then to 'id'.
    """
    if telegram_user_id:
        user = (
            db.query(User)
            .filter(User.telegram_user_id == telegram_user_id, User.is_active.is_(True))
            .first()
        )
        if user and user.language:
            lang = user.language.value if hasattr(user.language, 'value') else str(user.language)
            if lang in ("en", "id", "ru"):
                return lang

    # Try factory language from group chat
    if chat_id:
        factory = (
            db.query(Factory)
            .filter(
                (Factory.masters_group_chat_id == chat_id) |
                (Factory.purchaser_chat_id == chat_id)
            )
            .first()
        )
        if factory and hasattr(factory, 'telegram_language') and factory.telegram_language:
            lang = factory.telegram_language
            if lang in ("en", "id", "ru"):
                return lang

    return _DEFAULT_LANG


def msg(key: str, lang: str = "id", **kwargs) -> str:
    """
    Get a translated message by key.
    Falls back: lang -> 'en' -> 'id' -> key itself.
    """
    templates = MESSAGES.get(key)
    if not templates:
        return key
    text = templates.get(lang) or templates.get("en") or templates.get("id") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text

# ────────────────────────────────────────────────────────────────
# Pending delivery confirmations (in-memory, expires after 30 min)
# ────────────────────────────────────────────────────────────────

_DELIVERY_TTL_SECONDS = 30 * 60  # 30 minutes

_pending_deliveries: dict[str, dict] = {}
# key   = unique delivery_id (short UUID)
# value = {
#     "created_at": float (time.time()),
#     "chat_id": int,
#     "factory_id": UUID,
#     "user_id": UUID | None,
#     "photo_id": UUID,
#     "readings": dict,         # raw Vision output
#     "matched_items": list,    # [{material_id, material_name, quantity, unit, ...}]
#     "unmatched_items": list,  # [{index, original_name, quantity, unit}]
# }


def _cleanup_expired_deliveries() -> None:
    """Remove pending deliveries older than TTL."""
    now = time.time()
    expired = [
        did for did, d in _pending_deliveries.items()
        if now - d["created_at"] > _DELIVERY_TTL_SECONDS
    ]
    for did in expired:
        del _pending_deliveries[did]
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired pending deliveries")


# ────────────────────────────────────────────────────────────────
# Pending delivery edit sessions (in-memory)
# ────────────────────────────────────────────────────────────────
# key = chat_id (int)
# value = {
#     "delivery_id": str,
#     "current_index": int,         # index into the combined items list
#     "awaiting": str | None,       # "material_name" | "material_type" | "material_subtype" | "qty" | None
#     "new_material_name": str,     # temp storage for Add New flow
#     "new_material_type": str,     # temp storage for Add New flow
#     "items": list[dict],          # ALL items (matched + unmatched), each has:
#         # "index": int, "original_name": str, "quantity": str, "unit": str,
#         # "material_id": str | None, "material_name": str | None,
#         # "status": "matched" | "unmatched" | "skipped"
# }
_pending_edits: dict[int, dict] = {}


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

async def handle_update(db: Session, update_data: dict) -> None:
    """
    Main dispatcher for incoming Telegram updates.
    Routes to the appropriate handler based on update type.
    """
    update_id = update_data.get("update_id", "?")
    logger.info(f"Telegram update #{update_id}: {_safe_summary(update_data)}")

    try:
        # Callback query (inline button press) — highest priority
        if "callback_query" in update_data:
            await handle_callback_query(db, update_data["callback_query"])
            return

        message = update_data.get("message")
        if not message:
            # edited_message, channel_post, etc. — ignore silently
            logger.debug(f"Ignoring non-message update #{update_id}")
            return

        # Photo message
        if message.get("photo"):
            await handle_photo(db, message)
            return

        # Text command
        text = (message.get("text") or "").strip()
        if text.startswith("/"):
            await handle_command(db, message)
            return

        # Check if this chat has an active delivery edit session awaiting text input
        msg_chat_id = message.get("chat", {}).get("id")
        if msg_chat_id and msg_chat_id in _pending_edits and text:
            edit_session = _pending_edits[msg_chat_id]
            if edit_session.get("awaiting"):
                await _handle_edit_text_input(db, msg_chat_id, text)
                return

        # Plain text in private chat — could be email for linking flow
        chat_type = message.get("chat", {}).get("type", "")
        if chat_type == "private" and text:
            await _handle_private_text(db, message)
            return

        logger.debug(f"Ignoring message type in update #{update_id}")

    except Exception as e:
        logger.error(f"Error handling update #{update_id}: {e}", exc_info=True)


async def handle_command(db: Session, message: dict) -> None:
    """Route /commands to specific handlers."""
    text = (message.get("text") or "").strip()
    chat_id = message["chat"]["id"]
    parts = text.split(maxsplit=1)
    command = parts[0].lower().split("@")[0]  # strip @botname suffix
    args = parts[1] if len(parts) > 1 else ""

    if command == "/start":
        await _cmd_start(db, message, args)
    elif command == "/status":
        await _cmd_status(db, message)
    elif command == "/help":
        await _cmd_help(db, message)
    elif command == "/stop":
        await _cmd_stop(db, message)
    elif command == "/defect":
        await _cmd_defect(db, message, args)
    elif command == "/actual":
        await _cmd_actual(db, message, args)
    elif command == "/split":
        await _cmd_split(db, message, args)
    elif command == "/glaze":
        await _cmd_glaze(db, message, args)
    elif command == "/recipe":
        await _cmd_recipe(db, message, args)
    elif command == "/plan":
        await _cmd_plan(db, message)
    elif command == "/photo":
        await _cmd_photo(db, message)
    else:
        _from = message.get("from", {})
        lang = get_user_language(db, _from.get("id"), chat_id)
        await _send_message(chat_id, msg("unknown_command", lang))


async def handle_photo(db: Session, message: dict) -> None:
    """
    Receive a photo from a master in a group chat.
    Downloads the file_id and creates a PositionPhoto record.
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")
    caption = (message.get("caption") or "").strip()

    # Get the highest-resolution photo (last in the array)
    photos = message.get("photo", [])
    if not photos:
        return
    best_photo = photos[-1]
    file_id = best_photo["file_id"]

    # Determine factory from group chat_id
    factory = (
        db.query(Factory)
        .filter(Factory.masters_group_chat_id == chat_id)
        .first()
    )
    if not factory:
        # Also check purchaser_chat_id
        factory = (
            db.query(Factory)
            .filter(Factory.purchaser_chat_id == chat_id)
            .first()
        )

    if not factory:
        # Private chat or unlinked group — try to find factory via user
        user = _find_user_by_telegram(db, telegram_user_id)
        if user:
            uf = (
                db.query(UserFactory)
                .filter(UserFactory.user_id == user.id)
                .first()
            )
            if uf:
                factory = db.query(Factory).filter(Factory.id == uf.factory_id).first()

    if not factory:
        logger.warning(f"Photo from unknown chat {chat_id}, user {telegram_user_id} — no factory found")
        lang = get_user_language(db, telegram_user_id, chat_id)
        await _send_message(chat_id, msg("cannot_determine_factory", lang))
        return

    # Look up the PMS user
    user = _find_user_by_telegram(db, telegram_user_id)

    # Determine photo_type from caption keywords
    photo_type = _detect_photo_type(caption)

    # Try to extract position reference from caption (e.g. #123, POS-123)
    position_id = None
    linked_position = None
    if caption and user:
        pos_ref = _extract_position_ref(caption)
        if pos_ref:
            linked_position = _find_position_by_number_or_id(db, pos_ref, user)
            if linked_position:
                position_id = linked_position.id

    # Create the photo record
    photo = PositionPhoto(
        factory_id=factory.id,
        telegram_file_id=file_id,
        telegram_chat_id=chat_id,
        uploaded_by_telegram_id=telegram_user_id,
        uploaded_by_user_id=user.id if user else None,
        photo_type=photo_type,
        caption=caption or None,
    )
    # Link to position if found (set position_id if the column exists)
    if position_id:
        try:
            photo.position_id = position_id
        except Exception:
            pass  # Column may not exist on model yet

    db.add(photo)
    db.commit()
    db.refresh(photo)

    logger.info(
        f"Photo saved: id={photo.id}, factory={factory.name}, "
        f"type={photo_type}, file_id={file_id[:20]}..."
        + (f", position={position_id}" if position_id else "")
    )

    # Upload to Supabase Storage (async, non-blocking for the user)
    try:
        image_bytes = await download_telegram_photo(file_id)
        if image_bytes:
            from business.services.photo_storage import upload_photo as storage_upload

            related_id = str(position_id) if position_id else str(photo.id)
            storage_result = await storage_upload(
                image_bytes=image_bytes,
                category="telegram",
                factory_id=factory.id,
                related_id=related_id,
                filename=f"{file_id[:20]}.jpg",
            )
            # Update photo record with Supabase URL
            if storage_result.get("url"):
                photo.photo_url = storage_result["url"]
                db.commit()
                logger.info(
                    f"Telegram photo uploaded to {storage_result['storage']}: "
                    f"{storage_result['path']}"
                )
    except Exception as e:
        logger.warning(f"Supabase upload for telegram photo failed (non-fatal): {e}")

    # Acknowledge receipt
    lang = get_user_language(db, telegram_user_id, chat_id)
    type_label = photo_type.replace("_", " ").title() if photo_type else "Photo"
    ack_msg = msg("photo_received", lang, type_label=type_label)
    if linked_position:
        pos_label = _format_position_label(linked_position)
        ack_msg += msg("photo_linked", lang, pos_label=pos_label)
    await _send_message(chat_id, ack_msg)

    # ── Delivery Photo — special handler ─────────────────────────
    if photo_type == "delivery":
        try:
            image_bytes_for_delivery = await download_telegram_photo(file_id)
            if image_bytes_for_delivery:
                await _handle_delivery_photo(
                    db, chat_id, factory, user,
                    image_bytes_for_delivery, photo, caption,
                )
        except Exception as e:
            logger.error(f"Delivery photo handler failed: {e}", exc_info=True)
            await _send_message(chat_id, msg("delivery_photo_failed", lang))
        return

    # ── LLM Photo Analysis ───────────────────────────────────────
    # Determine if this photo type warrants LLM analysis
    analysis_type_map = {
        "scale": "scale",
        "defect": "quality",
        "quality": "quality",
        "packing": "packing",
    }
    llm_analysis_type = analysis_type_map.get(photo_type)

    if llm_analysis_type:
        try:
            from business.services.photo_analysis import analyze_photo, format_analysis_message

            # Download the photo bytes from Telegram
            image_bytes = await download_telegram_photo(file_id)
            if image_bytes:
                # Build context for the analysis
                analysis_context = {}
                if linked_position:
                    analysis_context["position"] = _format_position_label(linked_position)
                    if hasattr(linked_position, "color") and linked_position.color:
                        analysis_context["expected_color"] = linked_position.color

                analysis_result = await analyze_photo(
                    image_bytes=image_bytes,
                    analysis_type=llm_analysis_type,
                    context=analysis_context if analysis_context else None,
                )

                if analysis_result:
                    pos_ref = _format_position_label(linked_position) if linked_position else None
                    analysis_msg = format_analysis_message(analysis_result, pos_ref)
                    await _send_message(chat_id, analysis_msg, parse_mode="")
                    logger.info(f"Photo analysis sent for photo {photo.id}")
                else:
                    logger.debug(f"Photo analysis returned None for photo {photo.id}")
            else:
                logger.warning(f"Could not download photo {file_id[:20]}... for analysis")
        except Exception as e:
            logger.error(f"LLM photo analysis failed: {e}", exc_info=True)
            # Analysis failure should not affect the main photo-saving flow


async def handle_callback_query(db: Session, callback_query: dict) -> None:
    """Handle inline button presses.

    Routes compact callback data prefixes to the appropriate handler:
      d:*  — daily distribution callbacks (ack, problem, detail)
      a:*  — alert callbacks (view position, reschedule kiln)
      t:*  — task callbacks (start, done, issue)
      link_confirm / task_done — legacy actions
    """
    callback_id = callback_query.get("id")
    data = callback_query.get("data", "")
    from_user = callback_query.get("from", {})
    telegram_user_id = from_user.get("id")

    logger.info(f"Callback query from {telegram_user_id}: data={data}")

    _cb_lang = get_user_language(db, telegram_user_id)

    # Parse callback data format: "action:param1:param2"
    parts = data.split(":", maxsplit=2)
    action = parts[0] if parts else ""

    # Route daily/alert/task callbacks to the dedicated handler service
    if action in ("d", "a", "t"):
        try:
            from business.services.telegram_callbacks import handle_callback
            response_text = handle_callback(db, callback_query)
            await answer_callback_query(callback_id, response_text)
        except Exception as e:
            logger.error(f"Callback handler error for data={data}: {e}", exc_info=True)
            await answer_callback_query(callback_id, msg("error_occurred", _cb_lang))
        return

    # Delivery confirmation callbacks
    if action in (
        "delivery_confirm", "delivery_cancel", "delivery_match", "delivery_new",
        "delivery_edit", "dedit",
    ):
        try:
            # Resolve chat_id from the callback_query message
            cb_message = callback_query.get("message", {})
            cb_chat_id = cb_message.get("chat", {}).get("id")
            if not cb_chat_id:
                await answer_callback_query(callback_id, msg("error_occurred", _cb_lang))
                return
            await _handle_delivery_callback(
                db, data, callback_id, cb_chat_id, telegram_user_id,
            )
        except Exception as e:
            logger.error(f"Delivery callback error for data={data}: {e}", exc_info=True)
            await answer_callback_query(callback_id, msg("error_occurred", _cb_lang))
        return

    if action == "link_confirm":
        # Future: confirm account linking
        await answer_callback_query(callback_id, "Account linked!")
    elif action == "task_done":
        # Future: mark task as done from Telegram
        await answer_callback_query(callback_id, "Task completion not yet implemented.")
    else:
        await answer_callback_query(callback_id, "OK")


async def answer_callback_query(
    callback_query_id: str,
    text: str,
    show_alert: bool = False,
) -> None:
    """Send answerCallbackQuery to Telegram API."""
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return

    url = f"{TELEGRAM_API.format(token=token)}/answerCallbackQuery"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                url,
                json={
                    "callback_query_id": callback_query_id,
                    "text": text,
                    "show_alert": show_alert,
                },
                timeout=10.0,
            )
    except Exception as e:
        logger.warning(f"answerCallbackQuery failed: {e}")


async def send_message_with_buttons(
    chat_id: int,
    text: str,
    inline_keyboard: list[list[dict]],
    parse_mode: str = "Markdown",
) -> Optional[dict]:
    """
    Send a message with InlineKeyboardMarkup.

    inline_keyboard format:
    [
        [{"text": "Button 1", "callback_data": "action:param"}],
        [{"text": "Button 2", "url": "https://..."}],
    ]
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return None

    url = f"{TELEGRAM_API.format(token=token)}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "reply_markup": {
            "inline_keyboard": inline_keyboard,
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"sendMessage with buttons failed: {data.get('description')}")
            return data
    except Exception as e:
        logger.warning(f"sendMessage with buttons failed: {e}")
        return None


async def download_telegram_photo(file_id: str) -> Optional[bytes]:
    """
    Download a photo from Telegram via getFile API.
    Returns the raw bytes, or None on failure.
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return None

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: get file path
            resp = await client.get(
                f"{TELEGRAM_API.format(token=token)}/getFile",
                params={"file_id": file_id},
                timeout=10.0,
            )
            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"getFile failed: {data.get('description')}")
                return None

            file_path = data["result"]["file_path"]

            # Step 2: download the file
            file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
            file_resp = await client.get(file_url, timeout=30.0)
            if file_resp.status_code == 200:
                return file_resp.content
            else:
                logger.warning(f"File download failed: HTTP {file_resp.status_code}")
                return None
    except Exception as e:
        logger.warning(f"download_telegram_photo failed: {e}")
        return None


def set_webhook(webhook_url: str) -> bool:
    """
    Register webhook URL with Telegram Bot API.
    Called synchronously on startup.
    Returns True if successful.
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.debug("set_webhook: TELEGRAM_BOT_TOKEN not configured, skipping")
        return False

    url = f"{TELEGRAM_API.format(token=token)}/setWebhook"
    try:
        resp = httpx.post(
            url,
            json={
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": False,
            },
            timeout=15.0,
        )
        data = resp.json()
        if data.get("ok"):
            logger.info(f"Telegram webhook set to: {webhook_url}")
            return True
        else:
            logger.warning(f"setWebhook failed: {data.get('description')}")
            return False
    except Exception as e:
        logger.warning(f"setWebhook failed: {e}")
        return False


# ────────────────────────────────────────────────────────────────
# Command handlers
# ────────────────────────────────────────────────────────────────

async def _cmd_start(db: Session, message: dict, args: str) -> None:
    """
    /start — Account linking flow (private) or welcome (group).
    /start {deep_link_code} — Deep linking (logged for future use).
    """
    chat_id = message["chat"]["id"]
    chat_type = message["chat"].get("type", "private")
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")
    first_name = from_user.get("first_name", "")

    if args:
        # Deep link — log for future use
        logger.info(f"Deep link start: user={telegram_user_id}, code={args}")
        await _send_message(
            chat_id,
            f"Welcome, {first_name}! Deep link code received: `{args}`\n"
            f"This feature is coming soon.",
        )
        return

    lang = get_user_language(db, telegram_user_id, chat_id)

    if chat_type != "private":
        # Group chat — just welcome
        await _send_message(chat_id, msg("group_welcome", lang))
        return

    # Private chat — check if already linked
    existing = _find_user_by_telegram(db, telegram_user_id)
    if existing:
        lang = existing.language.value if hasattr(existing.language, 'value') else str(existing.language) if existing.language else lang
        await _send_message(chat_id, msg("account_already_linked", lang, name=existing.name, email=existing.email))
        return

    # Ask for email to link
    await _send_message(chat_id, msg("welcome_start", lang, first_name=first_name))


async def _cmd_status(db: Session, message: dict) -> None:
    """
    /status — Show user's pending tasks.
    Queries Task where assigned_to = user.id and status not completed.
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    user = _find_user_by_telegram(db, telegram_user_id)
    lang = get_user_language(db, telegram_user_id, chat_id)
    if not user:
        await _send_message(chat_id, msg("account_not_linked", lang))
        return

    lang = user.language.value if hasattr(user.language, 'value') else str(user.language) if user.language else lang

    # Find pending/in-progress tasks assigned to this user
    tasks = (
        db.query(Task)
        .filter(
            Task.assigned_to == user.id,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        )
        .order_by(Task.priority.desc(), Task.created_at)
        .limit(20)
        .all()
    )

    if not tasks:
        await _send_message(chat_id, msg("no_pending_tasks", lang))
        return

    lines = [msg("your_tasks", lang)]
    for i, task in enumerate(tasks, 1):
        # Try to get order number if task has related_order_id
        order_label = ""
        position_label = ""
        if task.related_order_id:
            order = db.query(ProductionOrder).filter(
                ProductionOrder.id == task.related_order_id
            ).first()
            if order:
                order_label = f" {order.order_number}"
        if task.related_position_id:
            pos = db.query(OrderPosition).filter(
                OrderPosition.id == task.related_position_id
            ).first()
            if pos and pos.position_number:
                pos_label = f"#{pos.position_number}"
                if pos.split_index:
                    pos_label += f".{pos.split_index}"
                position_label = f" Pos {pos_label}"

        task_type_display = task.type.value.replace("_", " ").title() if task.type else "Task"
        status_icon = "" if task.status == TaskStatus.IN_PROGRESS else ""

        desc = task.description[:60] if task.description else task_type_display
        line = f"{i}. {status_icon}{order_label}{position_label} — {desc}"
        lines.append(line)

    await _send_message(chat_id, "\n".join(lines))

    # ── AI: Smart task prioritization ─────────────────────────────
    try:
        from business.services.telegram_ai import prioritize_tasks
        task_dicts = []
        for task in tasks:
            order_num = ""
            if task.related_order_id:
                order = db.query(ProductionOrder).filter(
                    ProductionOrder.id == task.related_order_id
                ).first()
                if order:
                    order_num = order.order_number
            task_dicts.append({
                "order_number": order_num,
                "type": task.type.value if task.type else "task",
                "description": (task.description or "")[:40],
                "status": task.status.value if task.status else "pending",
                "deadline": str(getattr(task, "deadline", "")) or "",
            })
        recommendation = await prioritize_tasks(
            tasks=task_dicts,
            kiln_schedule=[],
            material_stock={},
        )
        if recommendation:
            await _send_message(chat_id, f"\U0001f9e0 AI: {recommendation}", parse_mode="")
    except Exception as e:
        logger.debug("AI task prioritization failed (non-fatal): %s", e)


async def _cmd_help(db: Session, message: dict) -> None:
    """/help — List available commands."""
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    lang = get_user_language(db, from_user.get("id"), chat_id)
    await _send_message(chat_id, msg("help_text", lang))


async def _cmd_stop(db: Session, message: dict) -> None:
    """/stop — Unlink Telegram account."""
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    lang = get_user_language(db, telegram_user_id, chat_id)
    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, msg("account_not_connected", lang))
        return

    lang = user.language.value if hasattr(user.language, 'value') else str(user.language) if user.language else lang
    user.telegram_user_id = None
    db.commit()
    logger.info(f"User {user.email} unlinked Telegram account {telegram_user_id}")

    await _send_message(chat_id, msg("account_unlinked", lang))


# ────────────────────────────────────────────────────────────────
# New command handlers (§37)
# ────────────────────────────────────────────────────────────────

async def _cmd_defect(db: Session, message: dict, args: str) -> None:
    """
    /defect <position_id> <defect_percent> — Report defect for a position.
    Example: /defect 12345 8   (8% defect for position #12345)
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    lang = get_user_language(db, telegram_user_id, chat_id)
    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, msg("account_not_linked", lang))
        return

    lang = user.language.value if hasattr(user.language, 'value') else str(user.language) if user.language else lang

    parts = args.split()
    if len(parts) < 2:
        await _send_message(chat_id, msg("defect_format", lang))
        return

    pos_id_str = parts[0]
    try:
        defect_pct = float(parts[1])
    except ValueError:
        await _send_message(chat_id, msg("defect_must_be_number", lang))
        return

    position = _find_position_by_number_or_id(db, pos_id_str, user)
    if not position:
        await _send_message(chat_id, msg("position_not_found", lang, pos=pos_id_str))
        return

    # Convert percentage to fraction for the service
    defect_fraction = defect_pct / 100.0

    try:
        from business.services.defect_coefficient import record_actual_defect_and_check_threshold
        result = record_actual_defect_and_check_threshold(
            db, position, defect_fraction,
        )
        db.commit()

        pos_label = _format_position_label(position)
        target_pct = result.get('target_pct', 0)
        actual_pct = result.get('actual_pct', 0)

        defect_msg = msg("defect_recorded", lang, pct=actual_pct, pos=pos_label, target=target_pct)
        if result.get('exceeded'):
            defect_msg += msg("defect_exceeded", lang)
        await _send_message(chat_id, defect_msg)

        # ── AI: Defect diagnostics ────────────────────────────────
        try:
            from business.services.telegram_ai import diagnose_defect
            position_info = {
                "color": getattr(position, "color", None) or "unknown",
                "size": getattr(position, "size", None) or "unknown",
                "recipe_name": getattr(position, "recipe_name", None) or "unknown",
                "kiln_name": "unknown",
            }
            # Gather recent defects from same factory (lightweight query)
            recent_defects = []
            kiln_history = []
            diagnosis = await diagnose_defect(
                position_info=position_info,
                defect_percent=defect_pct,
                recent_defects=recent_defects,
                kiln_history=kiln_history,
            )
            if diagnosis:
                await _send_message(chat_id, f"\U0001f9e0 AI: {diagnosis}", parse_mode="")
        except Exception as e:
            logger.debug("AI defect diagnosis failed (non-fatal): %s", e)

    except Exception as e:
        logger.error(f"Error in /defect: {e}", exc_info=True)
        db.rollback()
        await _send_message(chat_id, msg("defect_record_failed", lang, error=str(e)))


async def _cmd_actual(db: Session, message: dict, args: str) -> None:
    """
    /actual <position_id> <quantity> — Record actual output quantity.
    Example: /actual 12345 95
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    lang = get_user_language(db, telegram_user_id, chat_id)
    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, msg("account_not_linked", lang))
        return

    lang = user.language.value if hasattr(user.language, 'value') else str(user.language) if user.language else lang

    parts = args.split()
    if len(parts) < 2:
        await _send_message(chat_id, msg("actual_format", lang))
        return

    pos_id_str = parts[0]
    try:
        actual_qty = int(parts[1])
    except ValueError:
        await _send_message(chat_id, msg("actual_must_be_int", lang))
        return

    position = _find_position_by_number_or_id(db, pos_id_str, user)
    if not position:
        await _send_message(chat_id, msg("position_not_found", lang, pos=pos_id_str))
        return

    try:
        planned_qty = position.quantity
        # Update actual output on the position
        # Use raw SQL for actual_output field which may exist on the table
        from sqlalchemy import text
        db.execute(
            text("""
                UPDATE order_positions
                SET actual_output = :actual_qty,
                    updated_at = NOW()
                WHERE id = :id
            """),
            {'actual_qty': actual_qty, 'id': str(position.id)},
        )
        db.commit()

        pos_label = _format_position_label(position)
        actual_msg = msg("actual_recorded", lang, actual=actual_qty, pos=pos_label, planned=planned_qty)
        if actual_qty < planned_qty:
            diff = planned_qty - actual_qty
            actual_msg += msg("actual_deficit", lang, diff=diff)
        await _send_message(chat_id, actual_msg)

    except Exception as e:
        logger.error(f"Error in /actual: {e}", exc_info=True)
        db.rollback()
        await _send_message(chat_id, msg("actual_record_failed", lang, error=str(e)))


async def _cmd_split(db: Session, message: dict, args: str) -> None:
    """
    /split <position_id> <qty1> <qty2> [qty3...] — Quick production split.
    Example: /split 12345 50 30 20
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    lang = get_user_language(db, telegram_user_id, chat_id)
    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, msg("account_not_linked", lang))
        return

    lang = user.language.value if hasattr(user.language, 'value') else str(user.language) if user.language else lang

    parts = args.split()
    if len(parts) < 3:
        await _send_message(chat_id, msg("split_format", lang))
        return

    pos_id_str = parts[0]
    try:
        quantities = [int(p) for p in parts[1:]]
    except ValueError:
        await _send_message(chat_id, msg("all_must_be_int", lang))
        return

    if len(quantities) < 2:
        await _send_message(chat_id, msg("min_2_parts", lang))
        return

    position = _find_position_by_number_or_id(db, pos_id_str, user)
    if not position:
        await _send_message(chat_id, msg("position_not_found", lang, pos=pos_id_str))
        return

    try:
        from business.services.production_split import can_split_position, split_position_mid_production

        can_split, reason = can_split_position(position)
        if not can_split:
            await _send_message(chat_id, msg("cannot_split", lang, reason=reason))
            return

        total_qty = sum(quantities)
        if total_qty != position.quantity:
            await _send_message(chat_id, msg("split_total_mismatch", lang, total=total_qty, qty=position.quantity))
            return

        splits = [{'quantity': q} for q in quantities]
        children = split_position_mid_production(
            db, position, splits,
            reason="Split via Telegram",
            created_by_id=user.id,
        )
        db.commit()

        pos_label = _format_position_label(position)
        child_labels = []
        for child in children:
            cl = _format_position_label(child)
            child_labels.append(f"{cl} ({child.quantity})")

        await _send_message(chat_id, msg("split_success", lang, pos=pos_label, children=", ".join(child_labels)))

    except ValueError as e:
        db.rollback()
        await _send_message(chat_id, msg("split_failed", lang, error=str(e)))
    except Exception as e:
        logger.error(f"Error in /split: {e}", exc_info=True)
        db.rollback()
        await _send_message(chat_id, msg("split_failed", lang, error=str(e)))


async def _cmd_glaze(db: Session, message: dict, args: str) -> None:
    """
    /glaze <position_id> — Show glazing info for a position.
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    lang = get_user_language(db, telegram_user_id, chat_id)
    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, msg("account_not_linked", lang))
        return

    lang = user.language.value if hasattr(user.language, 'value') else str(user.language) if user.language else lang

    pos_id_str = args.strip()
    if not pos_id_str:
        await _send_message(chat_id, msg("glaze_format", lang))
        return

    position = _find_position_by_number_or_id(db, pos_id_str, user)
    if not position:
        await _send_message(chat_id, msg("position_not_found", lang, pos=pos_id_str))
        return

    pos_label = _format_position_label(position)
    lines = [msg("glaze_info_header", lang, pos=pos_label)]

    # Recipe info
    if position.recipe_id:
        recipe = db.query(Recipe).filter(Recipe.id == position.recipe_id).first()
        if recipe:
            lines.append(msg("recipe_label", lang, name=recipe.name))
            if recipe.recipe_type:
                lines.append(msg("type_label", lang, type=recipe.recipe_type))

            # Kiln config (temperature, duration)
            kiln_config = db.query(RecipeKilnConfig).filter(
                RecipeKilnConfig.recipe_id == recipe.id
            ).first()
            if kiln_config:
                if kiln_config.firing_temperature:
                    lines.append(msg("temperature_label", lang, temp=kiln_config.firing_temperature))
                if kiln_config.firing_duration_hours:
                    lines.append(msg("duration_label", lang, hours=kiln_config.firing_duration_hours))
                if kiln_config.two_stage_firing:
                    lines.append(msg("two_stage_yes", lang))

            # BOM / materials
            recipe_materials = (
                db.query(RecipeMaterial)
                .filter(RecipeMaterial.recipe_id == recipe.id)
                .all()
            )
            if recipe_materials:
                lines.append(msg("materials_label", lang))
                for rm in recipe_materials:
                    mat = db.query(Material).filter(Material.id == rm.material_id).first()
                    mat_name = mat.name if mat else "?"
                    lines.append(f"  - {mat_name}: {rm.quantity_per_unit} {rm.unit}")
        else:
            lines.append(msg("recipe_not_found", lang))
    else:
        lines.append(msg("recipe_not_set", lang))

    # Position glazing info
    lines.append(msg("color_label", lang, color=position.color or '-'))
    if position.color_2:
        lines.append(msg("color_2_label", lang, color=position.color_2))
    lines.append(msg("size_label", lang, size=position.size or '-'))
    lines.append(msg("qty_pcs", lang, qty=position.quantity))

    if position.planned_glazing_date:
        lines.append(msg("glaze_schedule", lang, date=position.planned_glazing_date))
    if position.two_stage_firing:
        tst = position.two_stage_type or "-"
        lines.append(msg("two_stage_type", lang, type=tst))

    status_val = position.status.value if hasattr(position.status, 'value') else str(position.status)
    lines.append(f"Status: {status_val}")

    await _send_message(chat_id, "\n".join(lines))


async def _cmd_recipe(db: Session, message: dict, args: str) -> None:
    """
    /recipe <collection> <color> [size] — Look up recipe.
    Example: /recipe Classic White 30x60
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    lang = get_user_language(db, telegram_user_id, chat_id)
    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, msg("account_not_linked", lang))
        return

    lang = user.language.value if hasattr(user.language, 'value') else str(user.language) if user.language else lang

    if not args.strip():
        await _send_message(chat_id, msg("recipe_search_format", lang))
        return

    parts = args.strip().split()
    if len(parts) < 2:
        await _send_message(chat_id, msg("recipe_min_args", lang))
        return

    # Parse: first word is collection, second is color, rest is optional size
    collection = parts[0]
    color = parts[1]
    size_filter = parts[2] if len(parts) > 2 else None

    # Search recipes by name/collection matching
    query = db.query(Recipe).filter(Recipe.is_active.is_(True))

    # Try matching collection in color_collection or name
    from sqlalchemy import or_
    query = query.filter(
        or_(
            Recipe.color_collection.ilike(f"%{collection}%"),
            Recipe.name.ilike(f"%{collection}%"),
        )
    )
    query = query.filter(Recipe.name.ilike(f"%{color}%"))

    recipes = query.limit(5).all()

    if not recipes:
        # Broader search: just match color in name
        recipes = (
            db.query(Recipe)
            .filter(
                Recipe.is_active.is_(True),
                Recipe.name.ilike(f"%{color}%"),
            )
            .limit(5)
            .all()
        )

    if not recipes:
        await _send_message(chat_id, msg("recipe_search_not_found", lang, query=f"{collection} {color}"))
        return

    for recipe in recipes:
        lines = [f"*{msg('recipe_label', lang, name=recipe.name)}*"]
        if recipe.color_collection:
            lines.append(msg("collection_label", lang, name=recipe.color_collection))
        if recipe.recipe_type:
            lines.append(msg("type_label", lang, type=recipe.recipe_type))

        # Kiln config
        kiln_config = db.query(RecipeKilnConfig).filter(
            RecipeKilnConfig.recipe_id == recipe.id
        ).first()
        if kiln_config:
            if kiln_config.firing_temperature:
                lines.append(msg("temperature_label", lang, temp=kiln_config.firing_temperature))
            if kiln_config.firing_duration_hours:
                lines.append(msg("duration_label", lang, hours=kiln_config.firing_duration_hours))

        # BOM
        recipe_materials = (
            db.query(RecipeMaterial)
            .filter(RecipeMaterial.recipe_id == recipe.id)
            .all()
        )
        if recipe_materials:
            lines.append(msg("materials_label", lang))
            for rm in recipe_materials:
                mat = db.query(Material).filter(Material.id == rm.material_id).first()
                mat_name = mat.name if mat else "?"
                lines.append(f"  - {mat_name}: {rm.quantity_per_unit} {rm.unit}")

        await _send_message(chat_id, "\n".join(lines))


async def _cmd_plan(db: Session, message: dict) -> None:
    """
    /plan — Show tomorrow's production plan for user's factory.
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")

    lang = get_user_language(db, telegram_user_id, chat_id)
    user = _find_user_by_telegram(db, telegram_user_id)
    if not user:
        await _send_message(chat_id, msg("account_not_linked", lang))
        return

    lang = user.language.value if hasattr(user.language, 'value') else str(user.language) if user.language else lang

    # Get user's factory
    uf = db.query(UserFactory).filter(UserFactory.user_id == user.id).first()
    if not uf:
        await _send_message(chat_id, msg("not_assigned_factory", lang))
        return

    factory = db.query(Factory).filter(Factory.id == uf.factory_id).first()
    if not factory:
        await _send_message(chat_id, msg("factory_not_found", lang))
        return

    tomorrow = date.today() + timedelta(days=1)

    # Check if there's a DailyTaskDistribution for tomorrow
    distribution = db.query(DailyTaskDistribution).filter(
        DailyTaskDistribution.factory_id == factory.id,
        DailyTaskDistribution.distribution_date == tomorrow,
    ).first()

    lines = [msg("plan_header", lang, date=tomorrow, factory=factory.name)]

    if distribution:
        # Use pre-computed distribution data
        glazing = distribution.glazing_tasks_json or []
        kiln = distribution.kiln_loading_json or []

        if glazing:
            lines.append(msg("glaze_section", lang, count=len(glazing)))
            for i, t in enumerate(glazing, 1):
                lines.append(
                    f"{i}. #{t.get('order_number', '?')} "
                    f"Pos #{t.get('position_label', t.get('position_number', ''))}"
                    f" | {t.get('color', '')} {t.get('size', '')}"
                    f" | {t.get('quantity', 0)} pcs"
                )

        if kiln:
            lines.append(msg("kiln_batch_section", lang, count=len(kiln)))
            for b in kiln:
                lines.append(
                    f"- {b.get('kiln_name', '?')}: "
                    f"{b.get('positions_count', 0)} pos, "
                    f"{b.get('temperature', 0)} C"
                )
    else:
        # Query positions directly from schedule
        glazing_positions = (
            db.query(OrderPosition)
            .filter(
                OrderPosition.factory_id == factory.id,
                OrderPosition.planned_glazing_date == tomorrow,
                OrderPosition.status.notin_([
                    PositionStatus.SHIPPED.value,
                    PositionStatus.CANCELLED.value,
                ]),
            )
            .order_by(OrderPosition.priority_order.desc())
            .limit(30)
            .all()
        )

        firing_positions = (
            db.query(OrderPosition)
            .filter(
                OrderPosition.factory_id == factory.id,
                OrderPosition.planned_kiln_date == tomorrow,
                OrderPosition.status.notin_([
                    PositionStatus.SHIPPED.value,
                    PositionStatus.CANCELLED.value,
                ]),
            )
            .order_by(OrderPosition.priority_order.desc())
            .limit(30)
            .all()
        )

        sorting_positions = (
            db.query(OrderPosition)
            .filter(
                OrderPosition.factory_id == factory.id,
                OrderPosition.planned_sorting_date == tomorrow,
                OrderPosition.status.notin_([
                    PositionStatus.SHIPPED.value,
                    PositionStatus.CANCELLED.value,
                ]),
            )
            .order_by(OrderPosition.priority_order.desc())
            .limit(30)
            .all()
        )

        if glazing_positions:
            lines.append(msg("glaze_section", lang, count=len(glazing_positions)))
            for i, pos in enumerate(glazing_positions, 1):
                pl = _format_position_label(pos)
                order_num = pos.order.order_number if pos.order else "?"
                lines.append(f"{i}. {order_num} {pl} | {pos.color or ''} {pos.size or ''} | {pos.quantity} pcs")

        if firing_positions:
            lines.append(msg("kiln_section", lang, count=len(firing_positions)))
            for i, pos in enumerate(firing_positions, 1):
                pl = _format_position_label(pos)
                order_num = pos.order.order_number if pos.order else "?"
                lines.append(f"{i}. {order_num} {pl} | {pos.color or ''} {pos.size or ''} | {pos.quantity} pcs")

        if sorting_positions:
            lines.append(msg("sorting_section", lang, count=len(sorting_positions)))
            for i, pos in enumerate(sorting_positions, 1):
                pl = _format_position_label(pos)
                order_num = pos.order.order_number if pos.order else "?"
                lines.append(f"{i}. {order_num} {pl} | {pos.quantity} pcs")

        if not glazing_positions and not firing_positions and not sorting_positions:
            lines.append(msg("no_plan_tomorrow", lang))

    await _send_message(chat_id, "\n".join(lines))


async def _cmd_photo(db: Session, message: dict) -> None:
    """
    /photo — Instructions for photo upload.
    Actual photo processing happens in handle_photo().
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    lang = get_user_language(db, from_user.get("id"), chat_id)
    await _send_message(chat_id, msg("photo_instructions", lang))


# ────────────────────────────────────────────────────────────────
# Private text handler (email linking flow)
# ────────────────────────────────────────────────────────────────

async def _handle_private_text(db: Session, message: dict) -> None:
    """
    Handle plain text in private chat — part of the /start email linking flow.
    If the text looks like an email, attempt to link the account.
    """
    chat_id = message["chat"]["id"]
    from_user = message.get("from", {})
    telegram_user_id = from_user.get("id")
    text = (message.get("text") or "").strip()

    lang = get_user_language(db, telegram_user_id, chat_id)

    # Check if already linked
    existing = _find_user_by_telegram(db, telegram_user_id)
    if existing:
        lang = existing.language.value if hasattr(existing.language, 'value') else str(existing.language) if existing.language else lang
        # ── AI: Try natural language command parsing ───────────────
        try:
            from business.services.telegram_ai import parse_natural_language
            user_context = {
                "user_name": existing.name,
                "role": existing.role.value if existing.role else None,
            }
            parsed = await parse_natural_language(text, user_context)
            if parsed:
                cmd = parsed.get("command")
                if cmd == "defect":
                    pos = parsed.get("position", "")
                    val = parsed.get("value", "")
                    args = f"{pos} {val}".strip()
                    await _cmd_defect(db, message, args)
                    return
                elif cmd == "actual":
                    pos = parsed.get("position", "")
                    val = parsed.get("value", "")
                    args = f"{pos} {val}".strip()
                    await _cmd_actual(db, message, args)
                    return
                elif cmd == "status":
                    await _cmd_status(db, message)
                    return
                elif cmd == "plan":
                    await _cmd_plan(db, message)
                    return
                elif cmd == "recipe":
                    query = parsed.get("query", "")
                    await _cmd_recipe(db, message, query)
                    return
                elif cmd == "help":
                    await _cmd_help(db, message)
                    return
        except Exception as e:
            logger.debug("AI NL parsing failed (non-fatal): %s", e)

        await _send_message(chat_id, msg("already_linked_msg", lang, name=existing.name))
        return

    # Check if it looks like an email
    if "@" not in text or "." not in text:
        await _send_message(chat_id, msg("send_email_prompt", lang))
        return

    email = text.lower().strip()

    # Look up user by email
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user:
        await _send_message(chat_id, msg("email_not_found", lang))
        return

    # Check if this user already has a different Telegram linked
    if user.telegram_user_id and user.telegram_user_id != telegram_user_id:
        await _send_message(chat_id, msg("already_linked_other", lang))
        return

    # Link the account
    user.telegram_user_id = telegram_user_id
    db.commit()
    logger.info(f"Linked Telegram {telegram_user_id} to user {user.email} (id={user.id})")

    # Use the newly linked user's language
    lang = user.language.value if hasattr(user.language, 'value') else str(user.language) if user.language else lang
    await _send_message(chat_id, msg("link_success", lang, name=user.name, email=user.email))


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def _find_user_by_telegram(db: Session, telegram_user_id: int) -> Optional[User]:
    """Find active User by telegram_user_id."""
    if not telegram_user_id:
        return None
    return (
        db.query(User)
        .filter(User.telegram_user_id == telegram_user_id, User.is_active.is_(True))
        .first()
    )


def _find_position_by_number_or_id(
    db: Session, identifier: str, user: "User"
) -> Optional["OrderPosition"]:
    """Find a position by position_number, UUID prefix, or POS-<number> format.

    Searches within the user's factory scope.
    """
    # Get user's factory IDs
    user_factories = (
        db.query(UserFactory.factory_id)
        .filter(UserFactory.user_id == user.id)
        .all()
    )
    factory_ids = [uf.factory_id for uf in user_factories]
    if not factory_ids:
        return None

    # Strip POS- prefix if present
    clean_id = identifier.strip()
    if clean_id.upper().startswith("POS-"):
        clean_id = clean_id[4:]
    if clean_id.startswith("#"):
        clean_id = clean_id[1:]

    # Try as position_number (integer)
    try:
        pos_num = int(clean_id)
        position = (
            db.query(OrderPosition)
            .filter(
                OrderPosition.position_number == pos_num,
                OrderPosition.factory_id.in_(factory_ids),
            )
            .order_by(OrderPosition.created_at.desc())
            .first()
        )
        if position:
            return position
    except ValueError:
        pass

    # Try as UUID prefix
    try:
        import sqlalchemy as sa
        from sqlalchemy import cast
        position = (
            db.query(OrderPosition)
            .filter(
                cast(OrderPosition.id, sa.String).like(f"{clean_id}%"),
                OrderPosition.factory_id.in_(factory_ids),
            )
            .first()
        )
        if position:
            return position
    except Exception:
        pass

    return None


def _format_position_label(position: "OrderPosition") -> str:
    """Format position label like #3 or #3.1."""
    if position.position_number:
        label = f"#{position.position_number}"
        if position.split_index:
            label += f".{position.split_index}"
        return label
    return f"#{str(position.id)[:8]}"


def _extract_position_ref(caption: str) -> Optional[str]:
    """Extract a position reference from caption text.

    Recognizes patterns like: #123, POS-123, pos123
    Returns the numeric/string part or None.
    """
    import re
    # Match #<number>, POS-<number>, or pos<number>
    match = re.search(r'(?:POS[- ]?|#)(\d+)', caption, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _auto_classify_material(db: Session, name: str) -> tuple:
    """Auto-classify a new material into a subgroup based on name keywords.

    Returns (subgroup_id, material_type) or (None, 'other').

    Keyword mapping:
    - frit/fritt → Frits subgroup
    - oxide/carbonate/iron/copper/cobalt/manganese → Oxides & Carbonates
    - pigment/color/warna → Pigments
    - stone/batu/tile → Stone
    - kaolin/clay/bentonite/cmc/silicate/zircosil → Other Bulk (additives)
    - box/kardus/label/sticker/tape → Packaging
    """
    from api.models import MaterialSubgroup

    name_lower = name.lower()

    # (keywords, subgroup_code, material_type)
    rules = [
        (["frit", "fritt"], "frit", "frit"),
        (["oxide", "carbonate", "iron", "copper", "cobalt", "manganese", "chrome"], "oxide_carbonate", "oxide"),
        (["pigment", "color", "warna", "stain"], "pigment", "pigment"),
        (["stone", "batu", "tile", "biscuit", "bisque"], "stone", "stone"),
        (["kaolin", "clay", "bentonite", "cmc", "silicate", "zircosil", "sodium"], "other_bulk", "additive"),
        (["box", "kardus", "label", "sticker", "tape", "pallet", "wrap"], "packaging", "packaging"),
        (["sink", "wash", "basin"], "sink", "finished_product"),
    ]

    for keywords, subgroup_code, mat_type in rules:
        if any(kw in name_lower for kw in keywords):
            sg = db.query(MaterialSubgroup).filter(MaterialSubgroup.code == subgroup_code).first()
            if sg:
                return sg.id, mat_type

    # Fallback: "Other" subgroup
    sg = db.query(MaterialSubgroup).filter(MaterialSubgroup.code == "other").first()
    return (sg.id if sg else None), "other"


def _fuzzy_match_material(db: Session, name: str) -> Optional[Material]:
    """
    Fuzzy-match a material name from a delivery note against the DB.

    Strategy:
      1. Exact match (case-insensitive)
      2. Contains match (material name contains the query or vice versa)
      3. Word-overlap match (at least 50% of words match)

    Returns the best-matching Material or None.
    """
    if not name or not name.strip():
        return None

    name_lower = name.strip().lower()

    # 1) Exact match (case-insensitive)
    all_materials = db.query(Material).all()
    for m in all_materials:
        if m.name.lower() == name_lower:
            return m

    # 2) Contains match
    for m in all_materials:
        m_lower = m.name.lower()
        if name_lower in m_lower or m_lower in name_lower:
            return m

    # 3) Word-overlap: at least 50% of query words found in material name
    query_words = set(name_lower.split())
    best_match = None
    best_overlap = 0.0
    for m in all_materials:
        m_words = set(m.name.lower().split())
        if not query_words:
            continue
        overlap = len(query_words & m_words) / len(query_words)
        if overlap > best_overlap and overlap >= 0.5:
            best_overlap = overlap
            best_match = m

    return best_match


async def _handle_delivery_photo(
    db: Session,
    chat_id: int,
    factory: Factory,
    user: Optional[User],
    image_bytes: bytes,
    photo: PositionPhoto,
    caption: str,
) -> None:
    """
    Process a delivery note photo — TWO-STEP confirmation flow:
    1. POST photo to /api/delivery/process-photo (Vision + smart matcher)
    2. Parse structured result into matched/unmatched items
    3. Store pending delivery and send PREVIEW with inline buttons
    4. Actual transactions are created only after PM clicks "Konfirmasi"
    """
    import os

    # Determine language from user
    lang = "id"
    if user and user.language:
        lang = user.language.value if hasattr(user.language, 'value') else str(user.language)

    # Cleanup expired pending deliveries on each new photo
    _cleanup_expired_deliveries()

    # ── Step 1: Call server-side delivery processing endpoint ─────
    base_url = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    if base_url:
        # Production: use public domain
        scheme = "https" if "railway" in base_url else "http"
        if not base_url.startswith("http"):
            api_url = f"{scheme}://{base_url}/api/delivery/process-photo"
        else:
            api_url = f"{base_url}/api/delivery/process-photo"
    else:
        # Local development
        port = os.getenv("PORT", "8080")
        api_url = f"http://localhost:{port}/api/delivery/process-photo"

    # Auth: use INTERNAL_API_KEY for server-to-server auth
    settings = get_settings()
    api_key = os.getenv("INTERNAL_API_KEY") or settings.OWNER_KEY
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    # Build query params
    params = {}
    if caption:
        params["supplier_hint"] = caption

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            files = {"file": ("delivery.jpg", image_bytes, "image/jpeg")}
            resp = await client.post(
                api_url, files=files, params=params, headers=headers,
            )
    except Exception as e:
        logger.error("Failed to call delivery API: %s", e, exc_info=True)
        await _send_message(chat_id, msg("delivery_server_error", lang), parse_mode="")
        return

    if resp.status_code != 200:
        logger.error(
            "Delivery API returned %d: %s", resp.status_code, resp.text[:500],
        )
        await _send_message(chat_id, msg("delivery_process_error", lang), parse_mode="")
        return

    result = resp.json()
    # result = {supplier, delivery_date, reference_number, items, total_items,
    #           matched_items (count), vision_raw, confidence}

    api_items = result.get("items", [])
    if not api_items:
        await _send_message(chat_id, msg("delivery_no_items", lang), parse_mode="")
        return

    # ── Step 2: Convert API response into matched/unmatched lists ─
    matched_items = []   # [{index, original_name, material_id, material_name, quantity, unit, ...}]
    unmatched_items = [] # [{index, original_name, quantity, unit, suggested_name, ...}]

    for idx, item in enumerate(api_items):
        delivery_name = item.get("delivery_name", item.get("name", ""))
        try:
            quantity = Decimal(str(item.get("quantity", 0)))
        except Exception:
            quantity = Decimal("0")
        unit = item.get("unit", "pcs")

        if quantity <= 0:
            continue

        if item.get("matched") and item.get("material_id"):
            # Size info for display
            size_label = ""
            if item.get("suggested_size_name"):
                if item.get("suggested_size_exists"):
                    size_label = f" ({item['suggested_size_name']} \u2705)"
                else:
                    size_label = f" ({item['suggested_size_name']} \u26a0\ufe0f baru)"

            matched_items.append({
                "index": idx,
                "original_name": delivery_name,
                "material_id": item["material_id"],
                "material_name": item.get("material_name", delivery_name),
                "quantity": str(quantity),
                "unit": unit,
                "size_label": size_label,
                "suggested_product_type": item.get("suggested_product_type"),
                "parsed_base_material": item.get("parsed_base_material"),
            })
        else:
            # Unmatched — include candidates for suggestion buttons
            candidates = item.get("candidates", [])
            unmatched_items.append({
                "index": idx,
                "original_name": delivery_name,
                "quantity": str(quantity),
                "unit": unit,
                "suggested_name": item.get("suggested_name"),
                "suggested_product_type": item.get("suggested_product_type"),
                "suggested_size_name": item.get("suggested_size_name"),
                "suggested_size_exists": item.get("suggested_size_exists", False),
                "needs_user_choice": item.get("needs_user_choice", False),
                "parsed_base_material": item.get("parsed_base_material"),
                "candidates": candidates,
            })

    # ── Step 3: Store pending delivery ────────────────────────────
    delivery_id = _uuid.uuid4().hex[:12]

    # Build readings dict from API response for downstream compatibility
    readings = result.get("vision_raw", {})
    readings["supplier"] = result.get("supplier") or readings.get("supplier", "")
    readings["reference_number"] = result.get("reference_number") or readings.get("reference_number", "")
    readings["date"] = result.get("delivery_date") or readings.get("date", "")

    _pending_deliveries[delivery_id] = {
        "created_at": time.time(),
        "chat_id": chat_id,
        "factory_id": str(factory.id),
        "user_id": str(user.id) if user else None,
        "photo_id": str(photo.id),
        "readings": readings,
        "matched_items": matched_items,
        "unmatched_items": unmatched_items,
    }

    # ── Step 4: Send preview message with inline buttons ──────────
    supplier = readings.get("supplier") or msg("unknown_supplier", lang)
    ref_number = readings.get("reference_number") or "-"
    delivery_date = readings.get("date") or "-"
    total_items = len(matched_items) + len(unmatched_items)

    lines = [
        msg("delivery_header", lang, supplier=supplier),
        msg("delivery_ref", lang, ref=ref_number, date=delivery_date),
        "",
        msg("found_items", lang, count=total_items),
    ]

    item_num = 0
    for mi in matched_items:
        item_num += 1
        size_info = mi.get("size_label", "")
        lines.append(
            f"{item_num}. \u2705 {mi['original_name']} \u2014 {mi['quantity']} {mi['unit']}"
            f" (\u2192 {mi['material_name']}{size_info})"
        )

    for ui in unmatched_items:
        item_num += 1
        size_hint = ""
        if ui.get("suggested_size_name"):
            if ui.get("suggested_size_exists"):
                size_hint = f" | size: {ui['suggested_size_name']} \u2705"
            else:
                size_hint = f" | size: {ui['suggested_size_name']} \u26a0\ufe0f baru"
        suggested = ""
        if ui.get("suggested_name"):
            suggested = f"\n   {msg('suggestion_label', lang, name=ui['suggested_name'])}"
        lines.append(
            f"{item_num}. \u26a0\ufe0f \"{ui['original_name']}\" \u2014 {ui['quantity']} {ui['unit']}"
            f" ({msg('not_found_label', lang)}{size_hint}){suggested}"
        )

    preview_text = "\n".join(lines)

    # Main confirm / cancel / edit buttons
    # Store language in pending delivery for use in callbacks
    _pending_deliveries[delivery_id]["lang"] = lang

    keyboard = [
        [
            {"text": msg("confirm_receipt_btn", lang), "callback_data": f"delivery_confirm:{delivery_id}"},
        ],
        [
            {"text": msg("edit_items_btn", lang), "callback_data": f"delivery_edit:{delivery_id}"},
            {"text": msg("cancel_btn", lang), "callback_data": f"delivery_cancel:{delivery_id}"},
        ],
    ]

    await send_message_with_buttons(chat_id, preview_text, keyboard, parse_mode="")

    # ── Step 5: For each unmatched item, send suggestion buttons ──
    for ui in unmatched_items:
        ui_idx = ui["index"]

        # Use candidates from API response if available
        api_candidates = ui.get("candidates", [])

        suggestion_text = msg("material_not_found_prompt", lang, name=ui['original_name'])
        if ui.get("suggested_name"):
            suggestion_text += msg("standard_name_hint", lang, name=ui['suggested_name'])
        suggestion_text += msg("choose_or_create", lang)

        suggestion_rows = []
        row: list[dict] = []

        if api_candidates:
            # Use candidates from the smart matcher (already sorted by score)
            for cand in api_candidates[:5]:
                cand_id = cand.get("material_id") or cand.get("id", "")
                cand_name = cand.get("material_name") or cand.get("name", "?")
                btn = {
                    "text": cand_name,
                    "callback_data": f"delivery_match:{delivery_id}:{ui_idx}:{cand_id}",
                }
                row.append(btn)
                if len(row) >= 3:
                    suggestion_rows.append(row)
                    row = []
        else:
            # Fallback: query DB for suggestions
            suggestions = _suggest_materials(db, ui["original_name"], limit=5)
            for sug in suggestions:
                btn = {
                    "text": sug.name,
                    "callback_data": f"delivery_match:{delivery_id}:{ui_idx}:{sug.id}",
                }
                row.append(btn)
                if len(row) >= 3:
                    suggestion_rows.append(row)
                    row = []

        if row:
            suggestion_rows.append(row)

        # "Create New" button on its own row
        suggestion_rows.append([{
            "text": msg("create_new_btn", lang),
            "callback_data": f"delivery_new:{delivery_id}:{ui_idx}",
        }])

        await send_message_with_buttons(chat_id, suggestion_text, suggestion_rows, parse_mode="")

    logger.info(
        "Delivery photo processed via API: delivery_id=%s, "
        "%d matched, %d unmatched, factory=%s",
        delivery_id, len(matched_items), len(unmatched_items), factory.name,
    )


def _try_link_purchase_request(
    db: Session,
    material: Material,
    factory: Factory,
    received_qty,
) -> None:
    """
    Try to find an open MaterialPurchaseRequest for this material and update it.
    Looks for requests with status in (PENDING, APPROVED, SENT, IN_TRANSIT)
    that contain this material in their materials_json.
    """
    from decimal import Decimal

    open_statuses = [
        PurchaseStatus.PENDING,
        PurchaseStatus.APPROVED,
        PurchaseStatus.SENT,
        PurchaseStatus.IN_TRANSIT,
    ]
    try:
        requests = (
            db.query(MaterialPurchaseRequest)
            .filter(
                MaterialPurchaseRequest.factory_id == factory.id,
                MaterialPurchaseRequest.status.in_(open_statuses),
            )
            .order_by(MaterialPurchaseRequest.created_at.desc())
            .all()
        )

        material_id_str = str(material.id)
        for pr in requests:
            materials_json = pr.materials_json or []
            for mat_entry in materials_json:
                entry_mat_id = str(mat_entry.get("material_id", ""))
                if entry_mat_id == material_id_str:
                    # Found a matching purchase request — update status
                    pr.actual_delivery_date = date.today()
                    # Update received quantities
                    received_json = pr.received_quantity_json or []
                    received_json.append({
                        "material_id": material_id_str,
                        "quantity": float(received_qty),
                        "source": "telegram_delivery_photo",
                    })
                    pr.received_quantity_json = received_json

                    # Check if all items are received to update status
                    total_items = len(materials_json)
                    total_received = len(set(
                        r.get("material_id") for r in received_json
                    ))
                    if total_received >= total_items:
                        pr.status = PurchaseStatus.RECEIVED
                    elif total_received > 0:
                        pr.status = PurchaseStatus.PARTIALLY_RECEIVED

                    logger.info(
                        f"Linked delivery to purchase request {pr.id}, "
                        f"status → {pr.status.value}"
                    )
                    return  # Link to the first matching request only

    except Exception as e:
        logger.warning(f"Failed to link purchase request: {e}", exc_info=True)


def _suggest_materials(db: Session, query: str, limit: int = 5) -> list:
    """Find materials similar to the query string for unmatched delivery items."""
    if not query or not query.strip():
        return db.query(Material).order_by(Material.name).limit(limit).all()

    query_lower = query.strip().lower()

    # Search by ILIKE (contains)
    results = (
        db.query(Material)
        .filter(Material.name.ilike(f"%{query_lower}%"))
        .limit(limit)
        .all()
    )
    if results:
        return results

    # Try individual words
    words = query_lower.split()
    for word in words:
        if len(word) < 3:
            continue
        results = (
            db.query(Material)
            .filter(Material.name.ilike(f"%{word}%"))
            .limit(limit)
            .all()
        )
        if results:
            return results

    # Fallback: return most common materials
    return db.query(Material).order_by(Material.name).limit(limit).all()


async def _handle_delivery_callback(
    db: Session,
    callback_data: str,
    callback_id: str,
    chat_id: int,
    telegram_user_id: int,
) -> None:
    """
    Handle delivery confirmation inline button callbacks.

    Callback data formats:
      delivery_confirm:{id}
      delivery_cancel:{id}
      delivery_match:{id}:{item_index}:{material_id}
      delivery_new:{id}:{item_index}
    """
    _cleanup_expired_deliveries()

    parts = callback_data.split(":")
    action = parts[0]
    delivery_id = parts[1] if len(parts) > 1 else ""

    pending = _pending_deliveries.get(delivery_id)
    lang = get_user_language(db, telegram_user_id, chat_id)
    if pending:
        lang = pending.get("lang", lang)

    if not pending:
        await answer_callback_query(callback_id, msg("receipt_expired_short", lang))
        await _send_message(chat_id, msg("receipt_expired", lang))
        return

    # ── delivery_cancel ───────────────────────────────────────────
    if action == "delivery_cancel":
        del _pending_deliveries[delivery_id]
        # Clean up any active edit session for this chat
        if chat_id in _pending_edits and _pending_edits[chat_id].get("delivery_id") == delivery_id:
            del _pending_edits[chat_id]
        await answer_callback_query(callback_id, msg("cancel_btn", lang))
        await _send_message(chat_id, msg("receipt_cancelled", lang), parse_mode="")
        logger.info(f"Delivery {delivery_id} cancelled by user {telegram_user_id}")
        return

    # ── delivery_match:{id}:{item_index}:{material_id} ───────────
    if action == "delivery_match":
        item_index = int(parts[2]) if len(parts) > 2 else -1
        material_id = parts[3] if len(parts) > 3 else ""

        # Find the unmatched item and move it to matched
        target_item = None
        for ui in pending["unmatched_items"]:
            if ui["index"] == item_index:
                target_item = ui
                break

        if not target_item:
            await answer_callback_query(callback_id, msg("item_not_found", lang))
            return

        # Look up the selected material
        try:
            material = db.query(Material).filter(Material.id == material_id).first()
        except Exception:
            material = None

        if not material:
            await answer_callback_query(callback_id, msg("material_not_found", lang))
            return

        # Move from unmatched to matched
        pending["unmatched_items"].remove(target_item)
        pending["matched_items"].append({
            "index": target_item["index"],
            "original_name": target_item["original_name"],
            "material_id": str(material.id),
            "material_name": material.name,
            "quantity": target_item["quantity"],
            "unit": target_item.get("unit") or material.unit or "pcs",
        })

        await answer_callback_query(
            callback_id,
            f"\"{target_item['original_name']}\" \u2192 {material.name}",
        )
        await _send_message(chat_id, msg("mapped_to", lang, original=target_item['original_name'], material=material.name))
        logger.info(
            f"Delivery {delivery_id}: matched \"{target_item['original_name']}\" "
            f"-> {material.name} (id={material.id})"
        )
        return

    # ── delivery_new:{id}:{item_index} ────────────────────────────
    if action == "delivery_new":
        item_index = int(parts[2]) if len(parts) > 2 else -1

        target_item = None
        for ui in pending["unmatched_items"]:
            if ui["index"] == item_index:
                target_item = ui
                break

        if not target_item:
            await answer_callback_query(callback_id, msg("item_not_found", lang))
            return

        # Create new material with auto-classification into subgroup
        try:
            mat_name = target_item["original_name"].strip()
            mat_unit = target_item.get("unit") or "pcs"
            subgroup_id, material_type = _auto_classify_material(db, mat_name)

            new_material = Material(
                name=mat_name,
                unit=mat_unit,
                material_type=material_type,
                subgroup_id=subgroup_id,
            )
            db.add(new_material)
            db.flush()

            # Move from unmatched to matched
            pending["unmatched_items"].remove(target_item)
            pending["matched_items"].append({
                "index": target_item["index"],
                "original_name": target_item["original_name"],
                "material_id": str(new_material.id),
                "material_name": new_material.name,
                "quantity": target_item["quantity"],
                "unit": target_item.get("unit") or new_material.unit or "pcs",
            })

            db.commit()

            await answer_callback_query(callback_id, f"Material \"{new_material.name}\" created")
            await _send_message(chat_id, msg("new_material_created", lang, name=new_material.name, original=target_item['original_name']))
            logger.info(
                f"Delivery {delivery_id}: created new material \"{new_material.name}\" "
                f"(id={new_material.id}) for \"{target_item['original_name']}\""
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create new material: {e}", exc_info=True)
            await answer_callback_query(callback_id, msg("error_occurred", lang))
            await _send_message(chat_id, msg("failed_create_material", lang, error=str(e)), parse_mode="")
        return

    # ── delivery_confirm:{id} ─────────────────────────────────────
    if action == "delivery_confirm":
        if pending["unmatched_items"]:
            unmatched_names = ", ".join(
                f"\"{ui['original_name']}\"" for ui in pending["unmatched_items"]
            )
            await answer_callback_query(callback_id, msg("still_unmatched", lang), show_alert=True)
            await _send_message(chat_id, msg("unmatched_items_warning", lang, names=unmatched_names), parse_mode="")
            return

        # All items matched — execute transactions
        try:
            await _execute_delivery_transactions(db, pending)

            del _pending_deliveries[delivery_id]
            # Clean up any active edit session
            if chat_id in _pending_edits and _pending_edits[chat_id].get("delivery_id") == delivery_id:
                del _pending_edits[chat_id]

            await answer_callback_query(callback_id, "Penerimaan dikonfirmasi!")

            # Build confirmation message
            readings = pending["readings"]
            supplier = readings.get("supplier", "Tidak diketahui")
            ref_number = readings.get("reference_number", "-")

            lines = [
                msg("receipt_confirmed_header", lang, supplier=supplier),
                f"Ref: {ref_number}",
                "",
            ]
            for mi in pending["matched_items"]:
                lines.append(
                    f"  \u2022 {mi['material_name']} — {mi['quantity']} {mi['unit']}"
                )
            lines.append("")
            lines.append(msg("receipt_total", lang, count=len(pending['matched_items'])))

            await _send_message(chat_id, "\n".join(lines), parse_mode="")

            logger.info(
                f"Delivery {delivery_id} confirmed: "
                f"{len(pending['matched_items'])} items committed"
            )

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit delivery {delivery_id}: {e}", exc_info=True)
            await answer_callback_query(callback_id, msg("error_occurred", lang))
            await _send_message(chat_id, msg("receipt_save_failed", lang, error=str(e)), parse_mode="")
        return

    # ── delivery_edit:{id} — start editing items ────────────────
    if action == "delivery_edit":
        # Build edit items list from pending delivery
        items = _build_edit_items_list(pending)
        _pending_edits[chat_id] = {
            "delivery_id": delivery_id,
            "current_index": 0,
            "awaiting": None,
            "new_material_name": "",
            "new_material_type": "",
            "items": items,
            "lang": lang,
        }
        await answer_callback_query(callback_id, msg("edit_mode_active", lang, count=len(items))[:200])
        await _send_message(
            chat_id,
            msg("edit_mode_active", lang, count=len(items)),
            parse_mode="",
        )
        await _send_edit_item_prompt(chat_id, delivery_id, _pending_edits[chat_id])
        return

    # ── dedit:* — edit session callbacks ──────────────────────────
    if action == "dedit":
        await _handle_dedit_callback(db, callback_data, callback_id, chat_id, telegram_user_id)
        return

    # Unknown action
    await answer_callback_query(callback_id, "OK")


async def _execute_delivery_transactions(db: Session, pending: dict) -> None:
    """
    Execute the actual DB transactions for a confirmed delivery.
    Creates MaterialTransaction records, updates MaterialStock,
    and links to open purchase requests.
    """
    factory_id = pending["factory_id"]
    user_id = pending["user_id"]
    readings = pending["readings"]

    factory = db.query(Factory).filter(Factory.id == factory_id).first()
    if not factory:
        raise ValueError(f"Factory {factory_id} not found")

    for mi in pending["matched_items"]:
        material = db.query(Material).filter(Material.id == mi["material_id"]).first()
        if not material:
            logger.warning(f"Material {mi['material_id']} not found, skipping")
            continue

        quantity = Decimal(mi["quantity"])

        # Create receive transaction
        txn = MaterialTransaction(
            material_id=material.id,
            factory_id=factory.id,
            type=TransactionType.RECEIVE,
            quantity=quantity,
            notes=(
                f"Telegram delivery photo. "
                f"Ref: {readings.get('reference_number', '-')}. "
                f"Supplier: {readings.get('supplier', '-')}"
            ),
            created_by=user_id,
        )
        db.add(txn)

        # Update or create stock record
        stock = (
            db.query(MaterialStock)
            .filter(
                MaterialStock.material_id == material.id,
                MaterialStock.factory_id == factory.id,
            )
            .first()
        )
        if stock:
            stock.balance = (stock.balance or Decimal("0")) + quantity
        else:
            stock = MaterialStock(
                material_id=material.id,
                factory_id=factory.id,
                balance=quantity,
            )
            db.add(stock)

        db.flush()

        # Try to link with purchase requests
        _try_link_purchase_request(db, material, factory, quantity)

    db.commit()


def _detect_photo_type(caption: str) -> str:
    """Detect photo type from caption keywords."""
    if not caption:
        return "other"
    caption_lower = caption.lower()

    # Delivery / material receiving — check BEFORE generic "material" matches
    if any(kw in caption_lower for kw in (
        "delivery", "arriving", "arrived", "raw material", "receiving", "receipt",
        "barang", "tiba", "kirim", "kiriman", "surat jalan", "terima", "penerimaan",
        "приход", "поставка", "накладная", "доставка",
    )):
        return "delivery"
    if any(kw in caption_lower for kw in ("scale", "timbang", "berat", "weight")):
        return "scale"
    if any(kw in caption_lower for kw in ("glaz", "glasir", "engobe")):
        return "glazing"
    if any(kw in caption_lower for kw in ("fir", "bakar", "kiln", "oven")):
        return "firing"
    if any(kw in caption_lower for kw in ("defect", "cacat", "reject", "pecah", "retak")):
        return "defect"
    if any(kw in caption_lower for kw in ("pack", "kemas", "box")):
        return "packing"
    if any(kw in caption_lower for kw in ("quality", "qc", "kualitas")):
        return "quality"
    # "материал" alone (Russian) — treat as delivery context
    if "материал" in caption_lower or "material" in caption_lower:
        return "delivery"
    return "other"


async def _send_message(
    chat_id: int,
    text: str,
    parse_mode: str = "Markdown",
) -> Optional[dict]:
    """Send a plain text message via Telegram Bot API (async)."""
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.debug("_send_message: no bot token configured")
        return None

    url = f"{TELEGRAM_API.format(token=token)}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
                timeout=10.0,
            )
            data = resp.json()
            if not data.get("ok"):
                logger.warning(
                    f"sendMessage failed (chat={chat_id}): {data.get('description')}"
                )
            return data
    except Exception as e:
        logger.warning(f"sendMessage failed (chat={chat_id}): {e}")
        return None


# ────────────────────────────────────────────────────────────────
# Delivery Edit Flow
# ────────────────────────────────────────────────────────────────

async def _edit_telegram_message(
    chat_id: int,
    message_id: int,
    text: str,
    inline_keyboard: Optional[list[list[dict]]] = None,
    parse_mode: str = "",
) -> Optional[dict]:
    """Edit an existing Telegram message (text + optional inline keyboard)."""
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return None

    url = f"{TELEGRAM_API.format(token=token)}/editMessageText"
    payload: dict = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if inline_keyboard is not None:
        payload["reply_markup"] = {"inline_keyboard": inline_keyboard}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10.0)
            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"editMessageText failed: {data.get('description')}")
            return data
    except Exception as e:
        logger.warning(f"editMessageText failed: {e}")
        return None


def _build_edit_items_list(pending: dict) -> list[dict]:
    """Build a unified items list from matched + unmatched items in a pending delivery."""
    items = []
    for mi in pending["matched_items"]:
        items.append({
            "index": mi["index"],
            "original_name": mi["original_name"],
            "quantity": mi["quantity"],
            "unit": mi.get("unit", "pcs"),
            "material_id": mi["material_id"],
            "material_name": mi["material_name"],
            "status": "matched",
        })
    for ui in pending["unmatched_items"]:
        items.append({
            "index": ui["index"],
            "original_name": ui["original_name"],
            "quantity": ui["quantity"],
            "unit": ui.get("unit", "pcs"),
            "material_id": None,
            "material_name": None,
            "status": "unmatched",
        })
    # Sort by original index
    items.sort(key=lambda x: x["index"])
    return items


async def _send_edit_item_prompt(chat_id: int, delivery_id: str, edit_session: dict) -> None:
    """Send the prompt for editing the current item in the edit session."""
    items = edit_session["items"]
    current_idx = edit_session["current_index"]

    # Find the next non-skipped item starting from current_index
    while current_idx < len(items) and items[current_idx]["status"] == "skipped":
        current_idx += 1
    edit_session["current_index"] = current_idx

    if current_idx >= len(items):
        # All items processed — show done
        await _send_edit_summary(chat_id, delivery_id, edit_session)
        return

    item = items[current_idx]
    total = len(items)
    num = current_idx + 1

    status_icon = "\u2705" if item["status"] == "matched" else "\u26a0\ufe0f"
    match_info = ""
    if item["status"] == "matched":
        match_info = f"\n\u2192 {item['material_name']}"

    lang = edit_session.get("lang", "id")

    text = (
        f"{status_icon} Item {num}/{total}: {item['original_name']}\n"
        f"{msg('quantity_label', lang, qty=item['quantity'], unit=item['unit'])}"
        f"{match_info}\n\n"
        f"{msg('choose_action', lang)}"
    )

    # Use compact callback prefix "dedit" to stay within 64-byte Telegram limit
    # Format: dedit:{delivery_id}:{action}:{item_list_pos}
    pos = str(current_idx)
    keyboard = [
        [
            {"text": msg("search_db_btn", lang), "callback_data": f"dedit:{delivery_id}:match:{pos}"},
            {"text": msg("create_new_btn", lang), "callback_data": f"dedit:{delivery_id}:new:{pos}"},
        ],
        [
            {"text": msg("change_qty_btn", lang), "callback_data": f"dedit:{delivery_id}:qty:{pos}"},
            {"text": msg("skip_btn", lang), "callback_data": f"dedit:{delivery_id}:skip:{pos}"},
        ],
        [
            {"text": msg("finish_edit_btn", lang), "callback_data": f"dedit:{delivery_id}:done:0"},
        ],
    ]

    await send_message_with_buttons(chat_id, text, keyboard, parse_mode="")


async def _send_edit_summary(chat_id: int, delivery_id: str, edit_session: dict) -> None:
    """Show updated summary after editing, with Confirm/Cancel buttons."""
    pending = _pending_deliveries.get(delivery_id)
    lang = edit_session.get("lang", pending.get("lang", "id") if pending else "id")

    if not pending:
        await _send_message(chat_id, msg("receipt_expired_short", lang), parse_mode="")
        return

    # Sync edit_session items back to pending
    _sync_edit_to_pending(delivery_id, edit_session)

    # Remove edit session
    if chat_id in _pending_edits:
        del _pending_edits[chat_id]

    # Re-render preview
    readings = pending["readings"]
    supplier = readings.get("supplier") or msg("unknown_supplier", lang)
    ref_number = readings.get("reference_number", "-")
    delivery_date = readings.get("date", "-")

    matched = pending["matched_items"]
    unmatched = pending["unmatched_items"]
    total_items = len(matched) + len(unmatched)

    lines = [
        msg("edited_header", lang, supplier=supplier),
        msg("delivery_ref", lang, ref=ref_number, date=delivery_date),
        "",
        msg("found_items", lang, count=total_items),
    ]

    item_num = 0
    for mi in matched:
        item_num += 1
        lines.append(
            f"{item_num}. \u2705 {mi['original_name']} — {mi['quantity']} {mi['unit']}"
            f" (\u2192 {mi['material_name']})"
        )
    for ui in unmatched:
        item_num += 1
        lines.append(
            f"{item_num}. \u26a0\ufe0f \"{ui['original_name']}\" — {ui['quantity']} {ui['unit']}"
            f" ({msg('not_found_label', lang)})"
        )

    # Count skipped items from the edit session
    skipped_count = sum(
        1 for it in edit_session["items"] if it["status"] == "skipped"
    )
    if skipped_count:
        lines.append(f"\n{msg('items_skipped', lang, count=skipped_count)}")

    preview_text = "\n".join(lines)

    keyboard = [
        [
            {"text": msg("confirm_receipt_btn", lang), "callback_data": f"delivery_confirm:{delivery_id}"},
        ],
        [
            {"text": msg("edit_items_btn", lang), "callback_data": f"delivery_edit:{delivery_id}"},
            {"text": msg("cancel_btn", lang), "callback_data": f"delivery_cancel:{delivery_id}"},
        ],
    ]

    await send_message_with_buttons(chat_id, preview_text, keyboard, parse_mode="")


def _sync_edit_to_pending(delivery_id: str, edit_session: dict) -> None:
    """Sync the edit session items back to the pending delivery's matched/unmatched lists."""
    pending = _pending_deliveries.get(delivery_id)
    if not pending:
        return

    new_matched = []
    new_unmatched = []

    for item in edit_session["items"]:
        if item["status"] == "skipped":
            continue  # Skipped items are excluded entirely
        if item["status"] == "matched" and item["material_id"]:
            new_matched.append({
                "index": item["index"],
                "original_name": item["original_name"],
                "material_id": item["material_id"],
                "material_name": item["material_name"],
                "quantity": item["quantity"],
                "unit": item["unit"],
            })
        else:
            new_unmatched.append({
                "index": item["index"],
                "original_name": item["original_name"],
                "quantity": item["quantity"],
                "unit": item["unit"],
            })

    pending["matched_items"] = new_matched
    pending["unmatched_items"] = new_unmatched


async def _handle_edit_text_input(db: Session, chat_id: int, text: str) -> None:
    """Handle text input during a delivery edit session (material name, qty, etc.)."""
    edit_session = _pending_edits.get(chat_id)
    if not edit_session:
        return

    awaiting = edit_session.get("awaiting")
    delivery_id = edit_session["delivery_id"]
    current_idx = edit_session["current_index"]
    items = edit_session["items"]

    if current_idx >= len(items):
        edit_session["awaiting"] = None
        return

    item = items[current_idx]
    lang = edit_session.get("lang", "id")

    # ── Awaiting new quantity ─────────────────────────────────────
    if awaiting == "qty":
        text = text.strip()
        try:
            new_qty = Decimal(text)
            if new_qty <= 0:
                raise ValueError("non-positive")
        except Exception:
            await _send_message(chat_id, msg("enter_valid_number", lang), parse_mode="")
            return

        item["quantity"] = str(new_qty)
        edit_session["awaiting"] = None
        await _send_message(chat_id, msg("qty_changed", lang, name=item['original_name'], qty=new_qty, unit=item['unit']), parse_mode="")
        # Show item prompt again
        await _send_edit_item_prompt(chat_id, delivery_id, edit_session)
        return

    # ── Awaiting material name for Add New ────────────────────────
    if awaiting == "material_name":
        mat_name = text.strip()
        if not mat_name:
            await _send_message(chat_id, msg("enter_material_name", lang), parse_mode="")
            return
        edit_session["new_material_name"] = mat_name
        edit_session["awaiting"] = "material_type"

        # Show type selection buttons
        keyboard = [
            [
                {"text": "Stone", "callback_data": f"dedit:{delivery_id}:type:stone"},
                {"text": "Frit", "callback_data": f"dedit:{delivery_id}:type:frit"},
            ],
            [
                {"text": "Pigment", "callback_data": f"dedit:{delivery_id}:type:pigment"},
                {"text": "Other", "callback_data": f"dedit:{delivery_id}:type:other"},
            ],
        ]
        await send_message_with_buttons(chat_id, msg("choose_material_type", lang, name=mat_name), keyboard, parse_mode="")
        return

    # Unknown awaiting state — clear it
    edit_session["awaiting"] = None


async def _handle_dedit_callback(
    db: Session,
    callback_data: str,
    callback_id: str,
    chat_id: int,
    telegram_user_id: int,
) -> None:
    """
    Handle delivery edit inline button callbacks.

    Callback data format: dedit:{delivery_id}:{action}:{param}
    Actions: match, new, qty, skip, done, sel (select material), type, subtype
    """
    lang = get_user_language(db, telegram_user_id, chat_id)

    parts = callback_data.split(":")
    if len(parts) < 4:
        await answer_callback_query(callback_id, msg("data_invalid", lang))
        return

    delivery_id = parts[1]
    action = parts[2]
    param = parts[3]

    pending = _pending_deliveries.get(delivery_id)
    if not pending:
        await answer_callback_query(callback_id, msg("receipt_expired_short", lang))
        if chat_id in _pending_edits:
            del _pending_edits[chat_id]
        return

    lang = pending.get("lang", lang)
    edit_session = _pending_edits.get(chat_id)
    if edit_session:
        lang = edit_session.get("lang", lang)

    # ── Start edit session (delivery_edit:{delivery_id}) ──────────
    # This is handled below via action routing

    # ── "done" — finish editing ───────────────────────────────────
    if action == "done":
        if edit_session:
            await answer_callback_query(callback_id, msg("finish_edit_btn", lang))
            await _send_edit_summary(chat_id, delivery_id, edit_session)
        else:
            await answer_callback_query(callback_id, "OK")
        return

    # Ensure we have an active edit session for other actions
    if not edit_session or edit_session["delivery_id"] != delivery_id:
        await answer_callback_query(callback_id, msg("edit_session_not_found", lang))
        return

    items = edit_session["items"]

    # ── "skip" — skip current item ────────────────────────────────
    if action == "skip":
        idx = int(param)
        if 0 <= idx < len(items):
            items[idx]["status"] = "skipped"
            await answer_callback_query(callback_id, f"{msg('skip_btn', lang)}: {items[idx]['original_name']}")
            await _send_message(chat_id, f"\u23ed {items[idx]['original_name']}", parse_mode="")
        edit_session["current_index"] = idx + 1
        edit_session["awaiting"] = None
        await _send_edit_item_prompt(chat_id, delivery_id, edit_session)
        return

    # ── "qty" — change quantity ───────────────────────────────────
    if action == "qty":
        idx = int(param)
        edit_session["current_index"] = idx
        edit_session["awaiting"] = "qty"
        await answer_callback_query(callback_id, "OK")
        await _send_message(
            chat_id,
            f"{msg('change_qty_btn', lang)}: \"{items[idx]['original_name']}\" "
            f"({items[idx]['quantity']} {items[idx]['unit']}):",
            parse_mode="",
        )
        return

    # ── "match" — search DB for materials ─────────────────────────
    if action == "match":
        idx = int(param)
        edit_session["current_index"] = idx
        edit_session["awaiting"] = None
        item = items[idx]

        # Search materials by first significant word
        suggestions = _suggest_materials(db, item["original_name"], limit=5)

        if not suggestions:
            await answer_callback_query(callback_id, msg("material_not_found", lang))
            await _send_message(chat_id, msg("no_materials_found", lang, name=item['original_name']), parse_mode="")
            await _send_edit_item_prompt(chat_id, delivery_id, edit_session)
            return

        await answer_callback_query(callback_id, "OK")

        # Build suggestion buttons
        keyboard_rows = []
        for sug in suggestions:
            # Use compact format: dedit:{did}:sel:{item_pos}:{material_id_short}
            # Material ID might be long UUID - use first 12 chars
            mat_id_short = str(sug.id).replace("-", "")[:12]
            cb_data = f"dedit:{delivery_id}:sel:{idx}:{mat_id_short}"
            # Store full ID mapping in edit session for lookup
            if "mat_id_map" not in edit_session:
                edit_session["mat_id_map"] = {}
            edit_session["mat_id_map"][mat_id_short] = str(sug.id)

            keyboard_rows.append([{
                "text": f"{sug.name}",
                "callback_data": cb_data,
            }])

        # Back button
        keyboard_rows.append([{
            "text": msg("back_btn", lang),
            "callback_data": f"dedit:{delivery_id}:back:{idx}",
        }])

        await send_message_with_buttons(chat_id, msg("matching_materials", lang, name=item['original_name']), keyboard_rows, parse_mode="")
        return

    # ── "sel" — select a material from search results ─────────────
    if action == "sel":
        # Full format: dedit:{did}:sel:{idx}:{mat_id_short}
        if len(parts) >= 5:
            idx = int(parts[3])
            mat_id_short = parts[4]
        else:
            await answer_callback_query(callback_id, msg("data_invalid", lang))
            return

        full_mat_id = edit_session.get("mat_id_map", {}).get(mat_id_short)
        if not full_mat_id:
            await answer_callback_query(callback_id, msg("material_not_found", lang))
            return

        material = db.query(Material).filter(Material.id == full_mat_id).first()
        if not material:
            await answer_callback_query(callback_id, msg("material_not_found", lang))
            return

        if 0 <= idx < len(items):
            items[idx]["material_id"] = str(material.id)
            items[idx]["material_name"] = material.name
            items[idx]["status"] = "matched"

        await answer_callback_query(callback_id, f"\u2192 {material.name}")
        await _send_message(chat_id, f"\u2705 \"{items[idx]['original_name']}\" \u2192 {material.name}", parse_mode="")

        # Move to next item
        edit_session["current_index"] = idx + 1
        edit_session["awaiting"] = None
        await _send_edit_item_prompt(chat_id, delivery_id, edit_session)
        return

    # ── "back" — go back to current item prompt ───────────────────
    if action == "back":
        idx = int(param)
        edit_session["current_index"] = idx
        edit_session["awaiting"] = None
        await answer_callback_query(callback_id, msg("back_btn", lang))
        await _send_edit_item_prompt(chat_id, delivery_id, edit_session)
        return

    # ── "new" — start Add New material flow ───────────────────────
    if action == "new":
        idx = int(param)
        edit_session["current_index"] = idx
        edit_session["awaiting"] = "material_name"
        edit_session["new_material_name"] = ""
        edit_session["new_material_type"] = ""
        await answer_callback_query(callback_id, msg("create_new_btn", lang))
        await _send_message(chat_id, msg("enter_material_name_en", lang, name=items[idx]['original_name']), parse_mode="")
        return

    # ── "type" — material type selected in Add New flow ───────────
    if action == "type":
        mat_type = param  # "stone", "frit", "pigment", "other"
        edit_session["new_material_type"] = mat_type
        mat_name = edit_session.get("new_material_name", "")

        if mat_type in ("stone",):
            # Ask for subtype
            edit_session["awaiting"] = "material_subtype"
            keyboard = [
                [
                    {"text": "Tiles", "callback_data": f"dedit:{delivery_id}:sub:tiles"},
                    {"text": "Sinks", "callback_data": f"dedit:{delivery_id}:sub:sink"},
                ],
                [
                    {"text": "Table Top", "callback_data": f"dedit:{delivery_id}:sub:tabletop"},
                    {"text": "Other", "callback_data": f"dedit:{delivery_id}:sub:other"},
                ],
            ]
            await answer_callback_query(callback_id, mat_type)
            await send_message_with_buttons(chat_id, msg("choose_subtype", lang, name=mat_name, type=mat_type), keyboard, parse_mode="")
        else:
            # Create material directly
            await answer_callback_query(callback_id, mat_type)
            await _create_new_material_from_edit(db, chat_id, delivery_id, edit_session)
        return

    # ── "sub" — material subtype selected ─────────────────────────
    if action == "sub":
        edit_session["new_material_subtype"] = param
        await answer_callback_query(callback_id, param)
        await _create_new_material_from_edit(db, chat_id, delivery_id, edit_session)
        return

    # Unknown action
    await answer_callback_query(callback_id, "OK")


async def _create_new_material_from_edit(
    db: Session,
    chat_id: int,
    delivery_id: str,
    edit_session: dict,
) -> None:
    """Create a new material from the edit session's Add New flow."""
    items = edit_session["items"]
    current_idx = edit_session["current_index"]
    item = items[current_idx]

    mat_name = edit_session.get("new_material_name", item["original_name"]).strip()
    mat_unit = item.get("unit") or "pcs"

    try:
        subgroup_id, material_type = _auto_classify_material(db, mat_name)

        # Override type if user selected one
        user_type = edit_session.get("new_material_type", "")
        if user_type and user_type != "other":
            material_type = user_type

        new_material = Material(
            name=mat_name,
            unit=mat_unit,
            material_type=material_type,
            subgroup_id=subgroup_id,
        )
        db.add(new_material)
        db.flush()
        db.commit()

        # Update edit session item
        item["material_id"] = str(new_material.id)
        item["material_name"] = new_material.name
        item["status"] = "matched"

        _lang = edit_session.get("lang", "id")
        await _send_message(chat_id, msg("new_material_created", _lang, name=new_material.name, original=item['original_name']), parse_mode="")
        logger.info(
            f"Edit flow: created material \"{new_material.name}\" "
            f"(id={new_material.id}) for \"{item['original_name']}\""
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create material in edit flow: {e}", exc_info=True)
        _lang = edit_session.get("lang", "id")
        await _send_message(chat_id, msg("failed_create_material", _lang, error=str(e)), parse_mode="")

    # Clear temp state and move to next item
    edit_session["awaiting"] = None
    edit_session["new_material_name"] = ""
    edit_session["new_material_type"] = ""
    edit_session.pop("new_material_subtype", None)
    edit_session["current_index"] = current_idx + 1
    await _send_edit_item_prompt(chat_id, delivery_id, edit_session)


def _safe_summary(update_data: dict) -> str:
    """Create a safe log summary of a Telegram update (no sensitive data)."""
    parts = []
    if "message" in update_data:
        _msg = update_data["message"]
        chat = _msg.get("chat", {})
        parts.append(f"chat_type={chat.get('type')}")
        parts.append(f"chat_id={chat.get('id')}")
        if _msg.get("text"):
            text_preview = _msg["text"][:50]
            parts.append(f"text={text_preview!r}")
        if _msg.get("photo"):
            parts.append(f"photo_count={len(_msg['photo'])}")
        from_user = _msg.get("from", {})
        parts.append(f"from_id={from_user.get('id')}")
    elif "callback_query" in update_data:
        cq = update_data["callback_query"]
        parts.append(f"callback_data={cq.get('data', '')!r}")
        parts.append(f"from_id={cq.get('from', {}).get('id')}")
    return ", ".join(parts) or "empty"
