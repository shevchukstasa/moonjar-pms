"""Warehouse role onboarding content."""

SECTIONS = [
    "wh_overview", "wh_receiving", "wh_stock", "wh_finished_goods",
    "wh_reconciliation", "wh_shipments",
]

QUIZ_ANSWERS: dict[str, dict[str, str]] = {
    "wh_overview": {"q1": "materials_and_goods", "q2": "kg", "q3": "min_balance_alert"},
    "wh_receiving": {"q1": "verify_and_log", "q2": "purchase_request_match", "q3": "photo_documentation"},
    "wh_stock": {"q1": "reserved_available", "q2": "telegram_dashboard", "q3": "create_purchase_request"},
    "wh_finished_goods": {"q1": "after_final_qc", "q2": "by_order_collection", "q3": "count_and_grade"},
    "wh_reconciliation": {"q1": "system_vs_physical", "q2": "monthly", "q3": "adjustment_with_reason"},
    "wh_shipments": {"q1": "partial_or_full", "q2": "tracking_number", "q3": "delivery_photo"},
}

ONBOARDING_CONTENT = {
    "wh_overview": {
        "icon": "\U0001f3e0",
        "title": {"en": "Warehouse Overview", "id": "Ikhtisar Gudang", "ru": "\u041e\u0431\u0437\u043e\u0440 \u0441\u043a\u043b\u0430\u0434\u0430"},
        "slides": [
            {"title": {"en": "Your Role", "id": "Peran Anda", "ru": "\u0412\u0430\u0448\u0430 \u0440\u043e\u043b\u044c"}, "content": {"en": "As Warehouse staff, you manage the physical flow of materials and finished goods. You receive raw materials, track stock levels, store finished tiles, and prepare shipments. Accuracy is critical.", "id": "Sebagai staf Gudang, Anda mengelola alur fisik material dan barang jadi. Anda menerima bahan baku, melacak level stok, menyimpan ubin jadi, dan menyiapkan pengiriman.", "ru": "\u0412\u044b \u0443\u043f\u0440\u0430\u0432\u043b\u044f\u0435\u0442\u0435 \u0444\u0438\u0437\u0438\u0447\u0435\u0441\u043a\u0438\u043c \u043f\u043e\u0442\u043e\u043a\u043e\u043c \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432 \u0438 \u0433\u043e\u0442\u043e\u0432\u043e\u0439 \u043f\u0440\u043e\u0434\u0443\u043a\u0446\u0438\u0438. \u041f\u0440\u0438\u0451\u043c, \u0441\u0442\u043e\u043a, \u0445\u0440\u0430\u043d\u0435\u043d\u0438\u0435, \u043e\u0442\u0433\u0440\u0443\u0437\u043a\u0430. \u0422\u043e\u0447\u043d\u043e\u0441\u0442\u044c \u043a\u0440\u0438\u0442\u0438\u0447\u043d\u0430."}, "icon": "\U0001f4e6"},
            {"title": {"en": "Stock Measurement", "id": "Pengukuran Stok", "ru": "\u0418\u0437\u043c\u0435\u0440\u0435\u043d\u0438\u0435 \u0441\u0442\u043e\u043a\u0430"}, "content": {"en": "Materials are measured in kilograms (kg). Always weigh incoming materials accurately. The system tracks: current stock, reserved amount, available amount. When stock is below minimum balance, alerts fire.", "id": "Material diukur dalam kilogram (kg). Selalu timbang material masuk dengan akurat. Sistem melacak: stok saat ini, jumlah reservasi, jumlah tersedia.", "ru": "\u041c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b \u0438\u0437\u043c\u0435\u0440\u044f\u044e\u0442\u0441\u044f \u0432 \u043a\u0433. \u0412\u0441\u0435\u0433\u0434\u0430 \u0432\u0437\u0432\u0435\u0448\u0438\u0432\u0430\u0439\u0442\u0435 \u0442\u043e\u0447\u043d\u043e. \u0421\u0438\u0441\u0442\u0435\u043c\u0430: \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u0441\u0442\u043e\u043a, \u0440\u0435\u0437\u0435\u0440\u0432, \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e."}, "icon": "\u2696\ufe0f"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What do you manage in the warehouse?", "id": "Apa yang Anda kelola di gudang?", "ru": "\u0427\u0435\u043c \u0432\u044b \u0443\u043f\u0440\u0430\u0432\u043b\u044f\u0435\u0442\u0435 \u043d\u0430 \u0441\u043a\u043b\u0430\u0434\u0435?"}, "options": [
                {"value": "materials_and_goods", "label": {"en": "Raw materials and finished goods", "id": "Bahan baku dan barang jadi", "ru": "\u0421\u044b\u0440\u044c\u0451 \u0438 \u0433\u043e\u0442\u043e\u0432\u0430\u044f \u043f\u0440\u043e\u0434\u0443\u043a\u0446\u0438\u044f"}},
                {"value": "orders", "label": {"en": "Customer orders", "id": "Pesanan pelanggan", "ru": "\u0417\u0430\u043a\u0430\u0437\u044b \u043a\u043b\u0438\u0435\u043d\u0442\u043e\u0432"}},
                {"value": "employees", "label": {"en": "Employees", "id": "Karyawan", "ru": "\u0421\u043e\u0442\u0440\u0443\u0434\u043d\u0438\u043a\u043e\u0432"}},
            ]},
            {"id": "q2", "question": {"en": "In what unit are materials measured?", "id": "Dalam satuan apa material diukur?", "ru": "\u0412 \u043a\u0430\u043a\u0438\u0445 \u0435\u0434\u0438\u043d\u0438\u0446\u0430\u0445 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b?"}, "options": [
                {"value": "kg", "label": {"en": "Kilograms", "id": "Kilogram", "ru": "\u041a\u0438\u043b\u043e\u0433\u0440\u0430\u043c\u043c\u044b"}},
                {"value": "pieces", "label": {"en": "Pieces", "id": "Buah", "ru": "\u0428\u0442\u0443\u043a\u0438"}},
                {"value": "liters", "label": {"en": "Liters", "id": "Liter", "ru": "\u041b\u0438\u0442\u0440\u044b"}},
            ]},
            {"id": "q3", "question": {"en": "What happens when stock is low?", "id": "Apa yang terjadi saat stok rendah?", "ru": "\u0427\u0442\u043e \u043f\u0440\u0438 \u043d\u0438\u0437\u043a\u043e\u043c \u0441\u0442\u043e\u043a\u0435?"}, "options": [
                {"value": "min_balance_alert", "label": {"en": "Alert fires when below minimum balance", "id": "Peringatan muncul saat di bawah saldo minimum", "ru": "\u0410\u043b\u0435\u0440\u0442 \u043f\u0440\u0438 \u043f\u0430\u0434\u0435\u043d\u0438\u0438 \u043d\u0438\u0436\u0435 \u043c\u0438\u043d\u0438\u043c\u0443\u043c\u0430"}},
                {"value": "nothing", "label": {"en": "Nothing", "id": "Tidak ada", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e"}},
                {"value": "auto_order", "label": {"en": "Auto-orders from supplier", "id": "Pesanan otomatis dari supplier", "ru": "\u0410\u0432\u0442\u043e-\u0437\u0430\u043a\u0430\u0437 \u0443 \u043f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a\u0430"}},
            ]},
        ],
    },
    "wh_receiving": {
        "icon": "\U0001f4e5",
        "title": {"en": "Receiving Materials", "id": "Penerimaan Material", "ru": "\u041f\u0440\u0438\u0451\u043c\u043a\u0430 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432"},
        "slides": [
            {"title": {"en": "Receiving Process", "id": "Proses Penerimaan", "ru": "\u041f\u0440\u043e\u0446\u0435\u0441\u0441 \u043f\u0440\u0438\u0451\u043c\u043a\u0438"}, "content": {"en": "When materials arrive: 1) Verify against purchase request, 2) Weigh accurately, 3) Log in the system, 4) Take photo of delivery. Match the delivery to the purchase request in PMS.", "id": "Ketika material tiba: 1) Verifikasi dengan permintaan pembelian, 2) Timbang akurat, 3) Catat di sistem, 4) Foto pengiriman.", "ru": "\u041f\u0440\u0438 \u043f\u043e\u0441\u0442\u0443\u043f\u043b\u0435\u043d\u0438\u0438: 1) \u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u043f\u043e \u0437\u0430\u044f\u0432\u043a\u0435, 2) \u0412\u0437\u0432\u0435\u0441\u0438\u0442\u044c, 3) \u0412\u043d\u0435\u0441\u0442\u0438 \u0432 \u0441\u0438\u0441\u0442\u0435\u043c\u0443, 4) \u0421\u0444\u043e\u0442\u043e\u0433\u0440\u0430\u0444\u0438\u0440\u043e\u0432\u0430\u0442\u044c."}, "icon": "\U0001f69a"},
            {"title": {"en": "Delivery Photo OCR", "id": "OCR Foto Pengiriman", "ru": "OCR \u0444\u043e\u0442\u043e \u0434\u043e\u0441\u0442\u0430\u0432\u043a\u0438"}, "content": {"en": "Take a photo of the delivery note and send to the Telegram bot. OCR reads the items, matches them against the database, and lets you confirm quantities. Quick and accurate.", "id": "Ambil foto nota pengiriman dan kirim ke bot Telegram. OCR membaca item, mencocokkan dengan database.", "ru": "\u0421\u0444\u043e\u0442\u043e\u0433\u0440\u0430\u0444\u0438\u0440\u0443\u0439\u0442\u0435 \u043d\u0430\u043a\u043b\u0430\u0434\u043d\u0443\u044e, \u043e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0431\u043e\u0442\u0443. OCR \u043f\u0440\u043e\u0447\u0442\u0451\u0442 \u0438 \u0441\u043e\u043f\u043e\u0441\u0442\u0430\u0432\u0438\u0442 \u0441 \u0431\u0430\u0437\u043e\u0439."}, "icon": "\U0001f4f8"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What's the first step when materials arrive?", "id": "Langkah pertama saat material tiba?", "ru": "\u041f\u0435\u0440\u0432\u044b\u0439 \u0448\u0430\u0433 \u043f\u0440\u0438 \u043f\u043e\u0441\u0442\u0443\u043f\u043b\u0435\u043d\u0438\u0438?"}, "options": [
                {"value": "verify_and_log", "label": {"en": "Verify against purchase request, weigh, log in system", "id": "Verifikasi dengan permintaan pembelian, timbang, catat", "ru": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u043f\u043e \u0437\u0430\u044f\u0432\u043a\u0435, \u0432\u0437\u0432\u0435\u0441\u0438\u0442\u044c, \u0432\u043d\u0435\u0441\u0442\u0438"}},
                {"value": "store", "label": {"en": "Put in storage immediately", "id": "Simpan segera", "ru": "\u0421\u0440\u0430\u0437\u0443 \u043d\u0430 \u0441\u043a\u043b\u0430\u0434"}},
                {"value": "ignore", "label": {"en": "Ignore and wait for PM", "id": "Abaikan dan tunggu PM", "ru": "\u0416\u0434\u0430\u0442\u044c PM"}},
            ]},
            {"id": "q2", "question": {"en": "What should deliveries match against?", "id": "Pengiriman harus dicocokkan dengan apa?", "ru": "\u0421 \u0447\u0435\u043c \u0441\u0432\u0435\u0440\u044f\u0442\u044c \u043f\u043e\u0441\u0442\u0430\u0432\u043a\u0443?"}, "options": [
                {"value": "purchase_request_match", "label": {"en": "The purchase request in PMS", "id": "Permintaan pembelian di PMS", "ru": "\u0417\u0430\u044f\u0432\u043a\u0430 \u043d\u0430 \u0437\u0430\u043a\u0443\u043f\u043a\u0443 \u0432 PMS"}},
                {"value": "nothing", "label": {"en": "Nothing", "id": "Tidak ada", "ru": "\u041d\u0438 \u0441 \u0447\u0435\u043c"}},
                {"value": "verbal", "label": {"en": "Verbal agreement only", "id": "Hanya kesepakatan verbal", "ru": "\u0423\u0441\u0442\u043d\u0430\u044f \u0434\u043e\u0433\u043e\u0432\u043e\u0440\u0451\u043d\u043d\u043e\u0441\u0442\u044c"}},
            ]},
            {"id": "q3", "question": {"en": "Why take delivery photos?", "id": "Mengapa ambil foto pengiriman?", "ru": "\u0417\u0430\u0447\u0435\u043c \u0444\u043e\u0442\u043e \u0434\u043e\u0441\u0442\u0430\u0432\u043a\u0438?"}, "options": [
                {"value": "photo_documentation", "label": {"en": "OCR reads items and documentation proof", "id": "OCR membaca item dan bukti dokumentasi", "ru": "OCR \u0447\u0438\u0442\u0430\u0435\u0442 \u043f\u043e\u0437\u0438\u0446\u0438\u0438 + \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u043b\u044c\u043d\u043e\u0435 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435"}},
                {"value": "not_needed", "label": {"en": "Not needed", "id": "Tidak diperlukan", "ru": "\u041d\u0435 \u043d\u0443\u0436\u043d\u043e"}},
                {"value": "decoration", "label": {"en": "For decoration", "id": "Untuk dekorasi", "ru": "\u0414\u043b\u044f \u043a\u0440\u0430\u0441\u043e\u0442\u044b"}},
            ]},
        ],
    },
    "wh_stock": {
        "icon": "\U0001f4ca",
        "title": {"en": "Stock Management", "id": "Manajemen Stok", "ru": "\u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0441\u0442\u043e\u043a\u043e\u043c"},
        "slides": [
            {"title": {"en": "Reserved vs Available", "id": "Direservasi vs Tersedia", "ru": "\u0420\u0435\u0437\u0435\u0440\u0432 vs \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e"}, "content": {"en": "Stock has two states: reserved (earmarked for orders) and available (free to use). When an order is scheduled, materials are reserved. Available = Total - Reserved.", "id": "Stok memiliki dua status: direservasi (dicadangkan untuk pesanan) dan tersedia (bebas digunakan).", "ru": "\u0421\u0442\u043e\u043a \u0438\u043c\u0435\u0435\u0442 \u0434\u0432\u0430 \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f: \u0440\u0435\u0437\u0435\u0440\u0432 (\u043f\u043e\u0434 \u0437\u0430\u043a\u0430\u0437\u044b) \u0438 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e. \u0414\u043e\u0441\u0442\u0443\u043f\u043d\u043e = \u0412\u0441\u0435\u0433\u043e - \u0420\u0435\u0437\u0435\u0440\u0432."}, "icon": "\U0001f4e6"},
            {"title": {"en": "Low Stock Alerts", "id": "Peringatan Stok Rendah", "ru": "\u0410\u043b\u0435\u0440\u0442\u044b \u043d\u0438\u0437\u043a\u043e\u0433\u043e \u0441\u0442\u043e\u043a\u0430"}, "content": {"en": "When material drops below minimum balance: Telegram alert + dashboard warning. You should verify physically and notify PM to create a purchase request if needed.", "id": "Ketika material turun di bawah saldo minimum: peringatan Telegram + peringatan dashboard.", "ru": "\u041f\u0440\u0438 \u043f\u0430\u0434\u0435\u043d\u0438\u0438 \u043d\u0438\u0436\u0435 \u043c\u0438\u043d\u0438\u043c\u0443\u043c\u0430: \u0430\u043b\u0435\u0440\u0442 Telegram + \u043f\u0440\u0435\u0434\u0443\u043f\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u0435 \u043d\u0430 \u0434\u0430\u0448\u0431\u043e\u0440\u0434\u0435."}, "icon": "\u26a0\ufe0f"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What's the difference between reserved and available?", "id": "Apa perbedaan antara direservasi dan tersedia?", "ru": "\u0420\u0430\u0437\u043d\u0438\u0446\u0430 \u043c\u0435\u0436\u0434\u0443 \u0440\u0435\u0437\u0435\u0440\u0432\u043e\u043c \u0438 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u043c?"}, "options": [
                {"value": "reserved_available", "label": {"en": "Reserved is earmarked for orders, available is free", "id": "Direservasi untuk pesanan, tersedia bebas", "ru": "\u0420\u0435\u0437\u0435\u0440\u0432 \u043f\u043e\u0434 \u0437\u0430\u043a\u0430\u0437\u044b, \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e\u0435 \u0441\u0432\u043e\u0431\u043e\u0434\u043d\u043e"}},
                {"value": "same", "label": {"en": "They are the same", "id": "Mereka sama", "ru": "\u042d\u0442\u043e \u043e\u0434\u043d\u043e \u0438 \u0442\u043e \u0436\u0435"}},
                {"value": "no_reserved", "label": {"en": "There's no reservation system", "id": "Tidak ada sistem reservasi", "ru": "\u0421\u0438\u0441\u0442\u0435\u043c\u044b \u0440\u0435\u0437\u0435\u0440\u0432\u0430 \u043d\u0435\u0442"}},
            ]},
            {"id": "q2", "question": {"en": "How are you notified of low stock?", "id": "Bagaimana Anda diberitahu stok rendah?", "ru": "\u041a\u0430\u043a \u0443\u0437\u043d\u0430\u0442\u044c \u043e \u043d\u0438\u0437\u043a\u043e\u043c \u0441\u0442\u043e\u043a\u0435?"}, "options": [
                {"value": "telegram_dashboard", "label": {"en": "Telegram alert and dashboard warning", "id": "Peringatan Telegram dan dashboard", "ru": "\u0410\u043b\u0435\u0440\u0442 Telegram \u0438 \u0434\u0430\u0448\u0431\u043e\u0440\u0434"}},
                {"value": "email", "label": {"en": "Email only", "id": "Hanya email", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e email"}},
                {"value": "no_alert", "label": {"en": "No alerts", "id": "Tidak ada peringatan", "ru": "\u041d\u0435\u0442 \u0430\u043b\u0435\u0440\u0442\u043e\u0432"}},
            ]},
            {"id": "q3", "question": {"en": "What to do when material is insufficient?", "id": "Apa yang harus dilakukan saat material tidak cukup?", "ru": "\u0427\u0442\u043e \u0434\u0435\u043b\u0430\u0442\u044c \u043f\u0440\u0438 \u043d\u0435\u0445\u0432\u0430\u0442\u043a\u0435?"}, "options": [
                {"value": "create_purchase_request", "label": {"en": "Notify PM to create a purchase request", "id": "Beritahu PM untuk membuat permintaan pembelian", "ru": "\u0421\u043e\u043e\u0431\u0449\u0438\u0442\u044c PM \u0434\u043b\u044f \u0437\u0430\u044f\u0432\u043a\u0438 \u043d\u0430 \u0437\u0430\u043a\u0443\u043f\u043a\u0443"}},
                {"value": "wait", "label": {"en": "Wait", "id": "Tunggu", "ru": "\u0416\u0434\u0430\u0442\u044c"}},
                {"value": "substitute", "label": {"en": "Use any substitute", "id": "Gunakan pengganti", "ru": "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c \u0437\u0430\u043c\u0435\u043d\u0443"}},
            ]},
        ],
    },
    "wh_finished_goods": {
        "icon": "\u2705",
        "title": {"en": "Finished Goods", "id": "Barang Jadi", "ru": "\u0413\u043e\u0442\u043e\u0432\u0430\u044f \u043f\u0440\u043e\u0434\u0443\u043a\u0446\u0438\u044f"},
        "slides": [
            {"title": {"en": "After QC", "id": "Setelah QC", "ru": "\u041f\u043e\u0441\u043b\u0435 QC"}, "content": {"en": "Tiles that pass Final QC move to finished goods. Log them in the system with exact count per grade (A, B, C). Store by order and collection for easy retrieval.", "id": "Ubin yang lolos Final QC pindah ke barang jadi. Catat di sistem dengan jumlah tepat per grade. Simpan berdasarkan pesanan dan koleksi.", "ru": "\u041f\u043b\u0438\u0442\u043a\u0438 \u043f\u043e\u0441\u043b\u0435 QC \u2014 \u0432 \u0433\u043e\u0442\u043e\u0432\u0443\u044e \u043f\u0440\u043e\u0434\u0443\u043a\u0446\u0438\u044e. \u0412\u043d\u0435\u0441\u0438\u0442\u0435 \u0441 \u0442\u043e\u0447\u043d\u044b\u043c \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e\u043c \u043f\u043e \u0433\u0440\u0435\u0439\u0434\u0430\u043c. \u0425\u0440\u0430\u043d\u0438\u0442\u0435 \u043f\u043e \u0437\u0430\u043a\u0430\u0437\u0430\u043c."}, "icon": "\U0001f4e6"},
            {"title": {"en": "Storage Organization", "id": "Organisasi Penyimpanan", "ru": "\u041e\u0440\u0433\u0430\u043d\u0438\u0437\u0430\u0446\u0438\u044f \u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f"}, "content": {"en": "Group by order and collection. Label clearly. Keep ready-to-ship orders accessible. Track surplus tiles (extra from defect coefficient) separately.", "id": "Kelompokkan berdasarkan pesanan dan koleksi. Beri label jelas. Jaga pesanan siap kirim agar mudah diakses.", "ru": "\u0413\u0440\u0443\u043f\u043f\u0438\u0440\u0443\u0439\u0442\u0435 \u043f\u043e \u0437\u0430\u043a\u0430\u0437\u0430\u043c. \u041c\u0430\u0440\u043a\u0438\u0440\u0443\u0439\u0442\u0435. \u0413\u043e\u0442\u043e\u0432\u044b\u0435 \u043a \u043e\u0442\u0433\u0440\u0443\u0437\u043a\u0435 \u2014 \u0432 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e\u043c \u043c\u0435\u0441\u0442\u0435."}, "icon": "\U0001f3f7\ufe0f"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "When do tiles become finished goods?", "id": "Kapan ubin menjadi barang jadi?", "ru": "\u041a\u043e\u0433\u0434\u0430 \u043f\u043b\u0438\u0442\u043a\u0430 \u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0441\u044f \u0433\u043e\u0442\u043e\u0432\u043e\u0439?"}, "options": [
                {"value": "after_final_qc", "label": {"en": "After passing Final QC", "id": "Setelah lolos Final QC", "ru": "\u041f\u043e\u0441\u043b\u0435 \u043f\u0440\u043e\u0445\u043e\u0436\u0434\u0435\u043d\u0438\u044f Final QC"}},
                {"value": "after_firing", "label": {"en": "Right after firing", "id": "Langsung setelah pembakaran", "ru": "\u0421\u0440\u0430\u0437\u0443 \u043f\u043e\u0441\u043b\u0435 \u043e\u0431\u0436\u0438\u0433\u0430"}},
                {"value": "after_glazing", "label": {"en": "After glazing", "id": "Setelah glasir", "ru": "\u041f\u043e\u0441\u043b\u0435 \u0433\u043b\u0430\u0437\u0443\u0440\u043e\u0432\u043a\u0438"}},
            ]},
            {"id": "q2", "question": {"en": "How should finished goods be stored?", "id": "Bagaimana barang jadi harus disimpan?", "ru": "\u041a\u0430\u043a \u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0433\u043e\u0442\u043e\u0432\u0443\u044e \u043f\u0440\u043e\u0434\u0443\u043a\u0446\u0438\u044e?"}, "options": [
                {"value": "by_order_collection", "label": {"en": "By order and collection, labeled clearly", "id": "Berdasarkan pesanan dan koleksi, diberi label jelas", "ru": "\u041f\u043e \u0437\u0430\u043a\u0430\u0437\u0430\u043c \u0438 \u043a\u043e\u043b\u043b\u0435\u043a\u0446\u0438\u044f\u043c, \u0441 \u043c\u0430\u0440\u043a\u0438\u0440\u043e\u0432\u043a\u043e\u0439"}},
                {"value": "random", "label": {"en": "Random stacking", "id": "Ditumpuk acak", "ru": "\u0425\u0430\u043e\u0442\u0438\u0447\u043d\u043e"}},
                {"value": "one_pile", "label": {"en": "One big pile", "id": "Satu tumpukan besar", "ru": "\u041e\u0434\u043d\u043e\u0439 \u043a\u0443\u0447\u0435\u0439"}},
            ]},
            {"id": "q3", "question": {"en": "What details to log for finished goods?", "id": "Detail apa yang dicatat untuk barang jadi?", "ru": "\u0427\u0442\u043e \u0444\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u0442\u044c?"}, "options": [
                {"value": "count_and_grade", "label": {"en": "Exact count per grade (A, B, C)", "id": "Jumlah tepat per grade (A, B, C)", "ru": "\u0422\u043e\u0447\u043d\u043e\u0435 \u043a\u043e\u043b-\u0432\u043e \u043f\u043e \u0433\u0440\u0435\u0439\u0434\u0430\u043c (A, B, C)"}},
                {"value": "total_only", "label": {"en": "Just total count", "id": "Hanya total jumlah", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043e\u0431\u0449\u0435\u0435 \u043a\u043e\u043b-\u0432\u043e"}},
                {"value": "nothing", "label": {"en": "Nothing", "id": "Tidak ada", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e"}},
            ]},
        ],
    },
    "wh_reconciliation": {
        "icon": "\U0001f4cb",
        "title": {"en": "Stock Reconciliation", "id": "Rekonsiliasi Stok", "ru": "\u0418\u043d\u0432\u0435\u043d\u0442\u0430\u0440\u0438\u0437\u0430\u0446\u0438\u044f"},
        "slides": [
            {"title": {"en": "Why Reconcile", "id": "Mengapa Rekonsiliasi", "ru": "\u0417\u0430\u0447\u0435\u043c \u0438\u043d\u0432\u0435\u043d\u0442\u0430\u0440\u0438\u0437\u0430\u0446\u0438\u044f"}, "content": {"en": "Physical stock may differ from system records due to measurement errors, spillage, or unrecorded usage. Monthly reconciliation ensures accuracy. Compare system vs physical count.", "id": "Stok fisik mungkin berbeda dari catatan sistem. Rekonsiliasi bulanan memastikan akurasi.", "ru": "\u0424\u0438\u0437\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u0441\u0442\u043e\u043a \u043c\u043e\u0436\u0435\u0442 \u043e\u0442\u043b\u0438\u0447\u0430\u0442\u044c\u0441\u044f \u043e\u0442 \u0441\u0438\u0441\u0442\u0435\u043c\u044b. \u0415\u0436\u0435\u043c\u0435\u0441\u044f\u0447\u043d\u0430\u044f \u0441\u0432\u0435\u0440\u043a\u0430."}, "icon": "\U0001f50d"},
            {"title": {"en": "Reconciliation Process", "id": "Proses Rekonsiliasi", "ru": "\u041f\u0440\u043e\u0446\u0435\u0441\u0441 \u0441\u0432\u0435\u0440\u043a\u0438"}, "content": {"en": "Physically count/weigh each material. Enter actual quantity in the reconciliation page. System shows discrepancy. Add reason for any adjustment. PM reviews and approves.", "id": "Hitung/timbang setiap material. Masukkan jumlah aktual di halaman rekonsiliasi. Sistem menunjukkan perbedaan.", "ru": "\u041f\u0435\u0440\u0435\u0441\u0447\u0438\u0442\u0430\u0439\u0442\u0435/\u0432\u0437\u0432\u0435\u0441\u044c\u0442\u0435 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b. \u0412\u043d\u0435\u0441\u0438\u0442\u0435 \u0444\u0430\u043a\u0442. \u0421\u0438\u0441\u0442\u0435\u043c\u0430 \u043f\u043e\u043a\u0430\u0436\u0435\u0442 \u0440\u0430\u0441\u0445\u043e\u0436\u0434\u0435\u043d\u0438\u0435. \u0423\u043a\u0430\u0436\u0438\u0442\u0435 \u043f\u0440\u0438\u0447\u0438\u043d\u0443."}, "icon": "\U0001f4dd"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What does reconciliation compare?", "id": "Apa yang dibandingkan rekonsiliasi?", "ru": "\u0427\u0442\u043e \u0441\u0440\u0430\u0432\u043d\u0438\u0432\u0430\u0435\u0442 \u0441\u0432\u0435\u0440\u043a\u0430?"}, "options": [
                {"value": "system_vs_physical", "label": {"en": "System records vs physical count", "id": "Catatan sistem vs hitungan fisik", "ru": "\u0414\u0430\u043d\u043d\u044b\u0435 \u0441\u0438\u0441\u0442\u0435\u043c\u044b vs \u0444\u0438\u0437\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u043f\u043e\u0434\u0441\u0447\u0451\u0442"}},
                {"value": "old_vs_new", "label": {"en": "Old vs new stock", "id": "Stok lama vs baru", "ru": "\u0421\u0442\u0430\u0440\u044b\u0439 vs \u043d\u043e\u0432\u044b\u0439 \u0441\u0442\u043e\u043a"}},
                {"value": "nothing", "label": {"en": "Nothing specific", "id": "Tidak ada yang spesifik", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u043e\u0433\u043e"}},
            ]},
            {"id": "q2", "question": {"en": "How often should reconciliation be done?", "id": "Seberapa sering rekonsiliasi harus dilakukan?", "ru": "\u041a\u0430\u043a \u0447\u0430\u0441\u0442\u043e \u0441\u0432\u0435\u0440\u043a\u0430?"}, "options": [
                {"value": "monthly", "label": {"en": "Monthly", "id": "Bulanan", "ru": "\u0415\u0436\u0435\u043c\u0435\u0441\u044f\u0447\u043d\u043e"}},
                {"value": "yearly", "label": {"en": "Yearly", "id": "Tahunan", "ru": "\u0415\u0436\u0435\u0433\u043e\u0434\u043d\u043e"}},
                {"value": "never", "label": {"en": "Never", "id": "Tidak pernah", "ru": "\u041d\u0438\u043a\u043e\u0433\u0434\u0430"}},
            ]},
            {"id": "q3", "question": {"en": "What must be provided for adjustments?", "id": "Apa yang harus diberikan untuk penyesuaian?", "ru": "\u0427\u0442\u043e \u043d\u0443\u0436\u043d\u043e \u0434\u043b\u044f \u043a\u043e\u0440\u0440\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u043a\u0438?"}, "options": [
                {"value": "adjustment_with_reason", "label": {"en": "Actual quantity and reason for discrepancy", "id": "Jumlah aktual dan alasan perbedaan", "ru": "\u0424\u0430\u043a\u0442\u0438\u0447\u0435\u0441\u043a\u043e\u0435 \u043a\u043e\u043b-\u0432\u043e \u0438 \u043f\u0440\u0438\u0447\u0438\u043d\u0430"}},
                {"value": "just_number", "label": {"en": "Just the number", "id": "Hanya angkanya", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0447\u0438\u0441\u043b\u043e"}},
                {"value": "nothing", "label": {"en": "Nothing extra", "id": "Tidak ada tambahan", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e \u0434\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0433\u043e"}},
            ]},
        ],
    },
    "wh_shipments": {
        "icon": "\U0001f69a",
        "title": {"en": "Shipments", "id": "Pengiriman", "ru": "\u041e\u0442\u0433\u0440\u0443\u0437\u043a\u0438"},
        "slides": [
            {"title": {"en": "Preparing Shipments", "id": "Menyiapkan Pengiriman", "ru": "\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430 \u043e\u0442\u0433\u0440\u0443\u0437\u043a\u0438"}, "content": {"en": "Shipments can be partial or full. Pack tiles carefully to prevent damage. Enter tracking number, carrier, and expected delivery date in the system.", "id": "Pengiriman bisa parsial atau penuh. Kemas ubin dengan hati-hati. Masukkan nomor pelacakan, kurir, dan tanggal pengiriman.", "ru": "\u041e\u0442\u0433\u0440\u0443\u0437\u043a\u0438 \u043c\u043e\u0433\u0443\u0442 \u0431\u044b\u0442\u044c \u0447\u0430\u0441\u0442\u0438\u0447\u043d\u044b\u043c\u0438 \u0438\u043b\u0438 \u043f\u043e\u043b\u043d\u044b\u043c\u0438. \u0423\u043f\u0430\u043a\u043e\u0432\u044b\u0432\u0430\u0439\u0442\u0435 \u0430\u043a\u043a\u0443\u0440\u0430\u0442\u043d\u043e. \u0412\u043d\u0435\u0441\u0438\u0442\u0435 \u0442\u0440\u0435\u043a\u0438\u043d\u0433, \u043f\u0435\u0440\u0435\u0432\u043e\u0437\u0447\u0438\u043a\u0430, \u0434\u0430\u0442\u0443."}, "icon": "\U0001f4e6"},
            {"title": {"en": "Delivery Confirmation", "id": "Konfirmasi Pengiriman", "ru": "\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435 \u0434\u043e\u0441\u0442\u0430\u0432\u043a\u0438"}, "content": {"en": "After delivery, take a photo of the delivered goods at the client site. Upload via Telegram bot for documentation. This closes the shipment loop.", "id": "Setelah pengiriman, ambil foto barang yang dikirim di lokasi klien. Unggah via bot Telegram.", "ru": "\u041f\u043e\u0441\u043b\u0435 \u0434\u043e\u0441\u0442\u0430\u0432\u043a\u0438 \u2014 \u0444\u043e\u0442\u043e \u0443 \u043a\u043b\u0438\u0435\u043d\u0442\u0430. \u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u0435 \u0447\u0435\u0440\u0435\u0437 Telegram-\u0431\u043e\u0442."}, "icon": "\U0001f4f8"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What types of shipments are possible?", "id": "Jenis pengiriman apa yang mungkin?", "ru": "\u041a\u0430\u043a\u0438\u0435 \u0442\u0438\u043f\u044b \u043e\u0442\u0433\u0440\u0443\u0437\u043e\u043a?"}, "options": [
                {"value": "partial_or_full", "label": {"en": "Partial or full shipments", "id": "Pengiriman parsial atau penuh", "ru": "\u0427\u0430\u0441\u0442\u0438\u0447\u043d\u044b\u0435 \u0438\u043b\u0438 \u043f\u043e\u043b\u043d\u044b\u0435"}},
                {"value": "full_only", "label": {"en": "Full only", "id": "Hanya penuh", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043f\u043e\u043b\u043d\u044b\u0435"}},
                {"value": "partial_only", "label": {"en": "Partial only", "id": "Hanya parsial", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0447\u0430\u0441\u0442\u0438\u0447\u043d\u044b\u0435"}},
            ]},
            {"id": "q2", "question": {"en": "What must you enter for a shipment?", "id": "Apa yang harus dimasukkan untuk pengiriman?", "ru": "\u0427\u0442\u043e \u0432\u043d\u043e\u0441\u0438\u0442\u044c \u043f\u0440\u0438 \u043e\u0442\u0433\u0440\u0443\u0437\u043a\u0435?"}, "options": [
                {"value": "tracking_number", "label": {"en": "Tracking number, carrier, expected delivery date", "id": "Nomor pelacakan, kurir, tanggal pengiriman", "ru": "\u0422\u0440\u0435\u043a\u0438\u043d\u0433, \u043f\u0435\u0440\u0435\u0432\u043e\u0437\u0447\u0438\u043a, \u0434\u0430\u0442\u0430"}},
                {"value": "nothing", "label": {"en": "Nothing", "id": "Tidak ada", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e"}},
                {"value": "just_date", "label": {"en": "Just date", "id": "Hanya tanggal", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0434\u0430\u0442\u0443"}},
            ]},
            {"id": "q3", "question": {"en": "What closes the shipment loop?", "id": "Apa yang menutup siklus pengiriman?", "ru": "\u0427\u0442\u043e \u0437\u0430\u0432\u0435\u0440\u0448\u0430\u0435\u0442 \u0446\u0438\u043a\u043b \u043e\u0442\u0433\u0440\u0443\u0437\u043a\u0438?"}, "options": [
                {"value": "delivery_photo", "label": {"en": "Delivery photo uploaded via Telegram", "id": "Foto pengiriman diunggah via Telegram", "ru": "\u0424\u043e\u0442\u043e \u0434\u043e\u0441\u0442\u0430\u0432\u043a\u0438 \u0447\u0435\u0440\u0435\u0437 Telegram"}},
                {"value": "email", "label": {"en": "Email confirmation", "id": "Konfirmasi email", "ru": "\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435 \u043f\u043e email"}},
                {"value": "nothing", "label": {"en": "Nothing needed", "id": "Tidak diperlukan", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e"}},
            ]},
        ],
    },
}
