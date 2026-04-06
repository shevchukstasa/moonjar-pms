"""Production Manager onboarding content — moved from onboarding.py."""

SECTIONS = [
    "welcome", "navigation", "orders", "materials", "schedule", "kilns",
    "quality", "tasks", "telegram", "reports", "gamification", "advanced",
]

QUIZ_ANSWERS: dict[str, dict[str, str]] = {
    "welcome": {
        "q1": "production_management",
        "q2": "stone_tiles",
        "q3": "bali_java",
    },
    "navigation": {
        "q1": "sidebar",
        "q2": "manager_dashboard",
        "q3": "settings",
    },
    "orders": {
        "q1": "webhook_or_manual",
        "q2": "awaiting_recipe",
        "q3": "12_statuses",
        "q4": "backward_scheduling",
    },
    "materials": {
        "q1": "reserved",
        "q2": "create_purchase_request",
        "q3": "kg",
        "q4": "min_balance",
    },
    "schedule": {
        "q1": "fifo",
        "q2": "kiln",
        "q3": "backward",
        "q4": "auto_reschedule",
    },
    "kilns": {
        "q1": "temperature_and_capacity",
        "q2": "weekly",
        "q3": "cycles_tracking",
        "q4": "sic",
    },
    "quality": {
        "q1": "pre_kiln_final",
        "q2": "five_stages",
        "q3": "grinding_or_refire",
    },
    "tasks": {
        "q1": "blocking_tasks",
        "q2": "force_unblock",
        "q3": "ceo_notification",
    },
    "telegram": {
        "q1": "morning_briefing",
        "q2": "photo_ocr",
        "q3": "slash_commands",
    },
    "reports": {
        "q1": "analytics_dashboard",
        "q2": "export_pdf_excel",
        "q3": "lead_time",
    },
    "gamification": {
        "q1": "accuracy_scoring",
        "q2": "leaderboard",
        "q3": "daily_challenges",
        "q4": "jan_reset",
    },
    "advanced": {
        "q1": "temperature_groups",
        "q2": "zone_capacity",
        "q3": "defect_coefficient",
        "q4": "engobe_shelf_coating",
    },
}

ONBOARDING_CONTENT = {
    "welcome": {
        "icon": "\U0001f30b",
        "title": {"en": "Welcome to Moonjar PMS", "id": "Selamat Datang di Moonjar PMS", "ru": "\u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c \u0432 Moonjar PMS"},
        "slides": [
            {
                "title": {"en": "Your Role as Production Manager", "id": "Peran Anda sebagai Manajer Produksi", "ru": "\u0412\u0430\u0448\u0430 \u0440\u043e\u043b\u044c \u043a\u0430\u043a PM"},
                "content": {
                    "en": "As a Production Manager at Moonjar, you are the heartbeat of our stone tile factory. You oversee the entire production flow: from receiving orders to shipping finished goods. The PMS system is your command center.",
                    "id": "Sebagai Manajer Produksi di Moonjar, Anda adalah jantung pabrik ubin batu kami. Anda mengawasi seluruh alur produksi: dari menerima pesanan hingga pengiriman barang jadi. Sistem PMS adalah pusat komando Anda.",
                    "ru": "\u041a\u0430\u043a Production Manager \u0432 Moonjar, \u0432\u044b \u2014 \u0441\u0435\u0440\u0434\u0446\u0435 \u043d\u0430\u0448\u0435\u0439 \u0444\u0430\u0431\u0440\u0438\u043a\u0438. \u0412\u044b \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u0438\u0440\u0443\u0435\u0442\u0435 \u0432\u0435\u0441\u044c \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u0435\u043d\u043d\u044b\u0439 \u043f\u043e\u0442\u043e\u043a: \u043e\u0442 \u043f\u0440\u0438\u0451\u043c\u0430 \u0437\u0430\u043a\u0430\u0437\u043e\u0432 \u0434\u043e \u043e\u0442\u0433\u0440\u0443\u0437\u043a\u0438 \u0433\u043e\u0442\u043e\u0432\u043e\u0439 \u043f\u0440\u043e\u0434\u0443\u043a\u0446\u0438\u0438. PMS \u2014 \u0432\u0430\u0448 \u0446\u0435\u043d\u0442\u0440 \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f."
                },
                "icon": "\U0001f3af",
            },
            {
                "title": {"en": "What is Moonjar?", "id": "Apa itu Moonjar?", "ru": "\u0427\u0442\u043e \u0442\u0430\u043a\u043e\u0435 Moonjar?"},
                "content": {
                    "en": "Moonjar Design is a craft manufactory in Bali specializing in glazed lava stone tiles. Each tile is handmade with fire, stone, and the movement of a brush. We produce for hotels, villas, and restaurants across Southeast Asia.",
                    "id": "Moonjar Design adalah manufaktur kerajinan di Bali yang mengkhususkan diri dalam ubin batu lava berglasir. Setiap ubin dibuat dengan tangan menggunakan api, batu, dan gerakan kuas. Kami memproduksi untuk hotel, villa, dan restoran di seluruh Asia Tenggara.",
                    "ru": "Moonjar Design \u2014 \u0440\u0435\u043c\u0435\u0441\u043b\u0435\u043d\u043d\u0430\u044f \u043c\u0430\u043d\u0443\u0444\u0430\u043a\u0442\u0443\u0440\u0430 \u043d\u0430 \u0411\u0430\u043b\u0438, \u0441\u043f\u0435\u0446\u0438\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u044e\u0449\u0430\u044f\u0441\u044f \u043d\u0430 \u0433\u043b\u0430\u0437\u0443\u0440\u043e\u0432\u0430\u043d\u043d\u043e\u0439 \u043f\u043b\u0438\u0442\u043a\u0435 \u0438\u0437 \u043b\u0430\u0432\u043e\u0432\u043e\u0433\u043e \u043a\u0430\u043c\u043d\u044f. \u041a\u0430\u0436\u0434\u0430\u044f \u043f\u043b\u0438\u0442\u043a\u0430 \u0441\u043e\u0437\u0434\u0430\u043d\u0430 \u0432\u0440\u0443\u0447\u043d\u0443\u044e. \u041c\u044b \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u043c \u0434\u043b\u044f \u043e\u0442\u0435\u043b\u0435\u0439, \u0432\u0438\u043b\u043b \u0438 \u0440\u0435\u0441\u0442\u043e\u0440\u0430\u043d\u043e\u0432 \u043f\u043e \u0432\u0441\u0435\u0439 \u042e\u0412\u0410."
                },
                "icon": "\U0001f30b",
            },
            {
                "title": {"en": "Your Daily Workflow", "id": "Alur Kerja Harian Anda", "ru": "\u0412\u0430\u0448 \u0435\u0436\u0435\u0434\u043d\u0435\u0432\u043d\u044b\u0439 \u0440\u0430\u0431\u043e\u0447\u0438\u0439 \u043f\u0440\u043e\u0446\u0435\u0441\u0441"},
                "content": {
                    "en": "Every morning: check the dashboard for new orders, review blocking tasks, verify material stock, check kiln schedule. During the day: monitor production progress, handle quality checks, resolve issues. Evening: review daily summary via Telegram bot.",
                    "id": "Setiap pagi: periksa dashboard untuk pesanan baru, tinjau tugas yang terblokir, verifikasi stok material, periksa jadwal kiln. Siang hari: pantau kemajuan produksi, tangani pemeriksaan kualitas, selesaikan masalah. Sore: tinjau ringkasan harian via bot Telegram.",
                    "ru": "\u041a\u0430\u0436\u0434\u043e\u0435 \u0443\u0442\u0440\u043e: \u043f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0434\u0430\u0448\u0431\u043e\u0440\u0434, \u043d\u043e\u0432\u044b\u0435 \u0437\u0430\u043a\u0430\u0437\u044b, \u0431\u043b\u043e\u043a\u0438\u0440\u0443\u044e\u0449\u0438\u0435 \u0437\u0430\u0434\u0430\u0447\u0438, \u0441\u0442\u043e\u043a \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432, \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043f\u0435\u0447\u0435\u0439. \u0414\u043d\u0451\u043c: \u043c\u043e\u043d\u0438\u0442\u043e\u0440\u0438\u043d\u0433 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u0430, \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430. \u0412\u0435\u0447\u0435\u0440: \u043e\u0431\u0437\u043e\u0440 \u0434\u043d\u044f \u0447\u0435\u0440\u0435\u0437 Telegram-\u0431\u043e\u0442."
                },
                "icon": "\U0001f4c5",
            },
        ],
        "quiz": [
            {
                "id": "q1",
                "question": {"en": "What is the main purpose of Moonjar PMS?", "id": "Apa tujuan utama Moonjar PMS?", "ru": "\u0413\u043b\u0430\u0432\u043d\u043e\u0435 \u043d\u0430\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 Moonjar PMS?"},
                "options": [
                    {"value": "production_management", "label": {"en": "Production management for stone tile factory", "id": "Manajemen produksi pabrik ubin batu", "ru": "\u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u043e\u043c \u043f\u043b\u0438\u0442\u043a\u0438 \u0438\u0437 \u043a\u0430\u043c\u043d\u044f"}},
                    {"value": "accounting", "label": {"en": "Accounting software", "id": "Perangkat lunak akuntansi", "ru": "\u0411\u0443\u0445\u0433\u0430\u043b\u0442\u0435\u0440\u0441\u043a\u0438\u0439 \u0441\u043e\u0444\u0442"}},
                    {"value": "crm", "label": {"en": "Customer relationship management", "id": "Manajemen hubungan pelanggan", "ru": "CRM \u0441\u0438\u0441\u0442\u0435\u043c\u0430"}},
                ],
            },
            {
                "id": "q2",
                "question": {"en": "What does Moonjar Design produce?", "id": "Apa yang diproduksi Moonjar Design?", "ru": "\u0427\u0442\u043e \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442 Moonjar Design?"},
                "options": [
                    {"value": "stone_tiles", "label": {"en": "Glazed lava stone tiles", "id": "Ubin batu lava berglasir", "ru": "\u0413\u043b\u0430\u0437\u0443\u0440\u043e\u0432\u0430\u043d\u043d\u0443\u044e \u043f\u043b\u0438\u0442\u043a\u0443 \u0438\u0437 \u043b\u0430\u0432\u043e\u0432\u043e\u0433\u043e \u043a\u0430\u043c\u043d\u044f"}},
                    {"value": "ceramics", "label": {"en": "Ceramic dishes", "id": "Piring keramik", "ru": "\u041a\u0435\u0440\u0430\u043c\u0438\u0447\u0435\u0441\u043a\u0443\u044e \u043f\u043e\u0441\u0443\u0434\u0443"}},
                    {"value": "glass", "label": {"en": "Glass windows", "id": "Jendela kaca", "ru": "\u0421\u0442\u0435\u043a\u043b\u044f\u043d\u043d\u044b\u0435 \u043e\u043a\u043d\u0430"}},
                ],
            },
            {
                "id": "q3",
                "question": {"en": "Where are Moonjar factories located?", "id": "Di mana pabrik Moonjar berada?", "ru": "\u0413\u0434\u0435 \u0440\u0430\u0441\u043f\u043e\u043b\u043e\u0436\u0435\u043d\u044b \u0444\u0430\u0431\u0440\u0438\u043a\u0438 Moonjar?"},
                "options": [
                    {"value": "bali_java", "label": {"en": "Bali and Java, Indonesia", "id": "Bali dan Jawa, Indonesia", "ru": "\u0411\u0430\u043b\u0438 \u0438 \u042f\u0432\u0430, \u0418\u043d\u0434\u043e\u043d\u0435\u0437\u0438\u044f"}},
                    {"value": "china", "label": {"en": "China", "id": "Tiongkok", "ru": "\u041a\u0438\u0442\u0430\u0439"}},
                    {"value": "europe", "label": {"en": "Europe", "id": "Eropa", "ru": "\u0415\u0432\u0440\u043e\u043f\u0430"}},
                ],
            },
        ],
    },
    "navigation": {
        "icon": "\U0001f9ed",
        "title": {"en": "System Navigation", "id": "Navigasi Sistem", "ru": "\u041d\u0430\u0432\u0438\u0433\u0430\u0446\u0438\u044f \u043f\u043e \u0441\u0438\u0441\u0442\u0435\u043c\u0435"},
        "slides": [
            {
                "title": {"en": "Dashboard Overview", "id": "Ikhtisar Dashboard", "ru": "\u041e\u0431\u0437\u043e\u0440 \u0434\u0430\u0448\u0431\u043e\u0440\u0434\u0430"},
                "content": {
                    "en": "Your main dashboard shows: active orders count, blocking tasks, kiln utilization, material alerts. The sidebar gives quick access to all sections: Orders, Schedule, Kilns, Materials, Quality, Tasks, Reports.",
                    "id": "Dashboard utama Anda menampilkan: jumlah pesanan aktif, tugas yang terblokir, utilisasi kiln, peringatan material. Sidebar memberikan akses cepat ke semua bagian.",
                    "ru": "\u0413\u043b\u0430\u0432\u043d\u044b\u0439 \u0434\u0430\u0448\u0431\u043e\u0440\u0434 \u043f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442: \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0435 \u0437\u0430\u043a\u0430\u0437\u044b, \u0431\u043b\u043e\u043a\u0438\u0440\u0443\u044e\u0449\u0438\u0435 \u0437\u0430\u0434\u0430\u0447\u0438, \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0443 \u043f\u0435\u0447\u0435\u0439, \u0430\u043b\u0435\u0440\u0442\u044b \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432. \u0411\u043e\u043a\u043e\u0432\u0430\u044f \u043f\u0430\u043d\u0435\u043b\u044c \u0434\u0430\u0451\u0442 \u0431\u044b\u0441\u0442\u0440\u044b\u0439 \u0434\u043e\u0441\u0442\u0443\u043f \u043a\u043e \u0432\u0441\u0435\u043c \u0440\u0430\u0437\u0434\u0435\u043b\u0430\u043c."
                },
                "icon": "\U0001f4ca",
            },
            {
                "title": {"en": "Tabs and Quick Actions", "id": "Tab dan Aksi Cepat", "ru": "\u0412\u043a\u043b\u0430\u0434\u043a\u0438 \u0438 \u0431\u044b\u0441\u0442\u0440\u044b\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f"},
                "content": {
                    "en": "Most pages have tabs at the top for sub-sections. Look for the + button to create new items. Use the search bar to quickly find orders by number or client name. Filters help narrow down large lists.",
                    "id": "Sebagian besar halaman memiliki tab di atas untuk sub-bagian. Cari tombol + untuk membuat item baru. Gunakan bilah pencarian untuk menemukan pesanan dengan cepat.",
                    "ru": "\u041d\u0430 \u0431\u043e\u043b\u044c\u0448\u0438\u043d\u0441\u0442\u0432\u0435 \u0441\u0442\u0440\u0430\u043d\u0438\u0446 \u0435\u0441\u0442\u044c \u0432\u043a\u043b\u0430\u0434\u043a\u0438 \u0434\u043b\u044f \u043f\u043e\u0434\u0440\u0430\u0437\u0434\u0435\u043b\u043e\u0432. \u041a\u043d\u043e\u043f\u043a\u0430 + \u0441\u043e\u0437\u0434\u0430\u0451\u0442 \u043d\u043e\u0432\u044b\u0435 \u044d\u043b\u0435\u043c\u0435\u043d\u0442\u044b. \u041f\u043e\u0438\u0441\u043a \u043f\u043e\u043c\u043e\u0433\u0430\u0435\u0442 \u0431\u044b\u0441\u0442\u0440\u043e \u043d\u0430\u0439\u0442\u0438 \u0437\u0430\u043a\u0430\u0437."
                },
                "icon": "\u26a1",
            },
            {
                "title": {"en": "Settings & Profile", "id": "Pengaturan & Profil", "ru": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u0438 \u043f\u0440\u043e\u0444\u0438\u043b\u044c"},
                "content": {
                    "en": "Access Settings from the bottom of the sidebar. Here you can: change your language (English/Indonesian/Russian), link your Telegram account, set notification preferences, toggle dark mode.",
                    "id": "Akses Pengaturan dari bagian bawah sidebar. Di sini Anda dapat: mengubah bahasa, menghubungkan akun Telegram, mengatur preferensi notifikasi, mengaktifkan mode gelap.",
                    "ru": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b \u0432\u043d\u0438\u0437\u0443 \u0431\u043e\u043a\u043e\u0432\u043e\u0439 \u043f\u0430\u043d\u0435\u043b\u0438. \u0417\u0434\u0435\u0441\u044c \u043c\u043e\u0436\u043d\u043e: \u0441\u043c\u0435\u043d\u0438\u0442\u044c \u044f\u0437\u044b\u043a, \u043f\u0440\u0438\u0432\u044f\u0437\u0430\u0442\u044c Telegram, \u043d\u0430\u0441\u0442\u0440\u043e\u0438\u0442\u044c \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u044f, \u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0442\u0451\u043c\u043d\u0443\u044e \u0442\u0435\u043c\u0443."
                },
                "icon": "\u2699\ufe0f",
            },
        ],
        "quiz": [
            {
                "id": "q1",
                "question": {"en": "Where do you find the main navigation menu?", "id": "Di mana Anda menemukan menu navigasi utama?", "ru": "\u0413\u0434\u0435 \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0433\u043b\u0430\u0432\u043d\u043e\u0435 \u043c\u0435\u043d\u044e \u043d\u0430\u0432\u0438\u0433\u0430\u0446\u0438\u0438?"},
                "options": [
                    {"value": "sidebar", "label": {"en": "In the sidebar", "id": "Di sidebar", "ru": "\u0412 \u0431\u043e\u043a\u043e\u0432\u043e\u0439 \u043f\u0430\u043d\u0435\u043b\u0438"}},
                    {"value": "footer", "label": {"en": "In the footer", "id": "Di footer", "ru": "\u0412 \u043d\u0438\u0436\u043d\u0435\u043c \u043a\u043e\u043b\u043e\u043d\u0442\u0438\u0442\u0443\u043b\u0435"}},
                    {"value": "popup", "label": {"en": "In a popup menu", "id": "Di menu popup", "ru": "\u0412 \u0432\u0441\u043f\u043b\u044b\u0432\u0430\u044e\u0449\u0435\u043c \u043c\u0435\u043d\u044e"}},
                ],
            },
            {
                "id": "q2",
                "question": {"en": "What is the first page you see after login?", "id": "Halaman pertama yang Anda lihat setelah login?", "ru": "\u041a\u0430\u043a\u0430\u044f \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430 \u043e\u0442\u043a\u0440\u044b\u0432\u0430\u0435\u0442\u0441\u044f \u043f\u043e\u0441\u043b\u0435 \u0432\u0445\u043e\u0434\u0430?"},
                "options": [
                    {"value": "manager_dashboard", "label": {"en": "Manager Dashboard", "id": "Dashboard Manajer", "ru": "\u0414\u0430\u0448\u0431\u043e\u0440\u0434 \u043c\u0435\u043d\u0435\u0434\u0436\u0435\u0440\u0430"}},
                    {"value": "login_page", "label": {"en": "Login page again", "id": "Halaman login lagi", "ru": "\u0421\u043d\u043e\u0432\u0430 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430 \u0432\u0445\u043e\u0434\u0430"}},
                    {"value": "settings", "label": {"en": "Settings", "id": "Pengaturan", "ru": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438"}},
                ],
            },
            {
                "id": "q3",
                "question": {"en": "Where can you change your language preference?", "id": "Di mana Anda bisa mengubah bahasa?", "ru": "\u0413\u0434\u0435 \u043c\u043e\u0436\u043d\u043e \u0441\u043c\u0435\u043d\u0438\u0442\u044c \u044f\u0437\u044b\u043a?"},
                "options": [
                    {"value": "settings", "label": {"en": "In Settings page", "id": "Di halaman Pengaturan", "ru": "\u0412 \u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430\u0445"}},
                    {"value": "dashboard", "label": {"en": "On the Dashboard", "id": "Di Dashboard", "ru": "\u041d\u0430 \u0434\u0430\u0448\u0431\u043e\u0440\u0434\u0435"}},
                    {"value": "telegram", "label": {"en": "Only via Telegram", "id": "Hanya via Telegram", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0447\u0435\u0440\u0435\u0437 Telegram"}},
                ],
            },
        ],
    },
    "orders": {
        "icon": "\U0001f4e6",
        "title": {"en": "Orders & Positions", "id": "Pesanan & Posisi", "ru": "\u0417\u0430\u043a\u0430\u0437\u044b \u0438 \u043f\u043e\u0437\u0438\u0446\u0438\u0438"},
        "slides": [
            {
                "title": {"en": "How Orders Arrive", "id": "Bagaimana Pesanan Masuk", "ru": "\u041a\u0430\u043a \u043f\u043e\u0441\u0442\u0443\u043f\u0430\u044e\u0442 \u0437\u0430\u043a\u0430\u0437\u044b"},
                "content": {
                    "en": "Orders come in two ways: 1) Automatically via webhook from the Sales app (most common), 2) Manually created by you in the system. Each order contains positions - individual tile types with specific size, color, collection, and quantity.",
                    "id": "Pesanan masuk dua cara: 1) Otomatis via webhook dari aplikasi Sales, 2) Dibuat manual oleh Anda. Setiap pesanan berisi posisi - jenis ubin individual dengan ukuran, warna, koleksi, dan jumlah tertentu.",
                    "ru": "\u0417\u0430\u043a\u0430\u0437\u044b \u043f\u043e\u0441\u0442\u0443\u043f\u0430\u044e\u0442 \u0434\u0432\u0443\u043c\u044f \u043f\u0443\u0442\u044f\u043c\u0438: 1) \u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438 \u0447\u0435\u0440\u0435\u0437 webhook \u0438\u0437 Sales-\u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f, 2) \u0412\u0440\u0443\u0447\u043d\u0443\u044e. \u041a\u0430\u0436\u0434\u044b\u0439 \u0437\u0430\u043a\u0430\u0437 \u0441\u043e\u0434\u0435\u0440\u0436\u0438\u0442 \u043f\u043e\u0437\u0438\u0446\u0438\u0438 \u2014 \u0442\u0438\u043f\u044b \u043f\u043b\u0438\u0442\u043a\u0438 \u0441 \u0440\u0430\u0437\u043c\u0435\u0440\u043e\u043c, \u0446\u0432\u0435\u0442\u043e\u043c, \u043a\u043e\u043b\u043b\u0435\u043a\u0446\u0438\u0435\u0439 \u0438 \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e\u043c."
                },
                "icon": "\U0001f4e5",
            },
            {
                "title": {"en": "Position Status Machine", "id": "Mesin Status Posisi", "ru": "\u0421\u0442\u0430\u0442\u0443\u0441\u043d\u0430\u044f \u043c\u0430\u0448\u0438\u043d\u0430 \u043f\u043e\u0437\u0438\u0446\u0438\u0439"},
                "content": {
                    "en": "Each position goes through stages: new -> awaiting_recipe -> awaiting_materials -> scheduled -> in_production (unpacking -> engobe -> glazing -> drying -> edge_cleaning) -> awaiting_firing -> firing -> cooling -> quality_check -> finished / grinding / refire. Understanding these statuses is KEY to your job.",
                    "id": "Setiap posisi melewati tahapan: new -> awaiting_recipe -> awaiting_materials -> scheduled -> in_production -> awaiting_firing -> firing -> cooling -> quality_check -> finished. Memahami status ini KUNCI pekerjaan Anda.",
                    "ru": "\u041a\u0430\u0436\u0434\u0430\u044f \u043f\u043e\u0437\u0438\u0446\u0438\u044f \u043f\u0440\u043e\u0445\u043e\u0434\u0438\u0442 \u044d\u0442\u0430\u043f\u044b: new -> awaiting_recipe -> awaiting_materials -> scheduled -> in_production -> awaiting_firing -> firing -> cooling -> quality_check -> finished. \u041f\u043e\u043d\u0438\u043c\u0430\u043d\u0438\u0435 \u044d\u0442\u0438\u0445 \u0441\u0442\u0430\u0442\u0443\u0441\u043e\u0432 \u2014 \u041a\u041b\u042e\u0427 \u043a \u0432\u0430\u0448\u0435\u0439 \u0440\u0430\u0431\u043e\u0442\u0435."
                },
                "icon": "\U0001f504",
            },
            {
                "title": {"en": "Order Detail Page", "id": "Halaman Detail Pesanan", "ru": "\u0421\u0442\u0440\u0430\u043d\u0438\u0446\u0430 \u0434\u0435\u0442\u0430\u043b\u0435\u0439 \u0437\u0430\u043a\u0430\u0437\u0430"},
                "content": {
                    "en": "Click any order to see details: client info, deadline, all positions with their statuses. You can edit the order header, add/remove positions, change quantities, and track progress per position. Color-coded status badges help you instantly see what needs attention.",
                    "id": "Klik pesanan mana saja untuk melihat detail: info klien, tenggat waktu, semua posisi dengan statusnya. Anda bisa mengedit header pesanan, menambah/menghapus posisi.",
                    "ru": "\u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u043d\u0430 \u0437\u0430\u043a\u0430\u0437 \u0434\u043b\u044f \u0434\u0435\u0442\u0430\u043b\u0435\u0439: \u0438\u043d\u0444\u043e \u043e \u043a\u043b\u0438\u0435\u043d\u0442\u0435, \u0434\u0435\u0434\u043b\u0430\u0439\u043d, \u0432\u0441\u0435 \u043f\u043e\u0437\u0438\u0446\u0438\u0438 \u0441\u043e \u0441\u0442\u0430\u0442\u0443\u0441\u0430\u043c\u0438. \u041c\u043e\u0436\u043d\u043e \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a, \u0434\u043e\u0431\u0430\u0432\u043b\u044f\u0442\u044c \u043f\u043e\u0437\u0438\u0446\u0438\u0438."
                },
                "icon": "\U0001f4cb",
            },
            {
                "title": {"en": "Backward Scheduling", "id": "Penjadwalan Mundur", "ru": "\u041e\u0431\u0440\u0430\u0442\u043d\u043e\u0435 \u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435"},
                "content": {
                    "en": "When an order arrives with a deadline, the system automatically calculates backward from the deadline: shipping date -> QC date -> cooling -> firing date -> production start. This ensures you start work at exactly the right time.",
                    "id": "Ketika pesanan masuk dengan tenggat waktu, sistem otomatis menghitung mundur dari tenggat: tanggal pengiriman -> QC -> pendinginan -> tanggal pembakaran -> mulai produksi.",
                    "ru": "\u041a\u043e\u0433\u0434\u0430 \u0437\u0430\u043a\u0430\u0437 \u043f\u043e\u0441\u0442\u0443\u043f\u0430\u0435\u0442 \u0441 \u0434\u0435\u0434\u043b\u0430\u0439\u043d\u043e\u043c, \u0441\u0438\u0441\u0442\u0435\u043c\u0430 \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438 \u0441\u0447\u0438\u0442\u0430\u0435\u0442 \u043e\u0431\u0440\u0430\u0442\u043d\u043e \u043e\u0442 \u0434\u0435\u0434\u043b\u0430\u0439\u043d\u0430: \u043e\u0442\u0433\u0440\u0443\u0437\u043a\u0430 -> QC -> \u043e\u0441\u0442\u044b\u0432\u0430\u043d\u0438\u0435 -> \u043e\u0431\u0436\u0438\u0433 -> \u043d\u0430\u0447\u0430\u043b\u043e \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u0430."
                },
                "icon": "\u23ea",
            },
        ],
        "quiz": [
            {
                "id": "q1",
                "question": {"en": "How do orders arrive in PMS?", "id": "Bagaimana pesanan masuk ke PMS?", "ru": "\u041a\u0430\u043a \u0437\u0430\u043a\u0430\u0437\u044b \u043f\u043e\u043f\u0430\u0434\u0430\u044e\u0442 \u0432 PMS?"},
                "options": [
                    {"value": "webhook_or_manual", "label": {"en": "Via webhook from Sales app or manual creation", "id": "Via webhook dari aplikasi Sales atau dibuat manual", "ru": "\u0427\u0435\u0440\u0435\u0437 webhook \u0438\u0437 Sales \u0438\u043b\u0438 \u0432\u0440\u0443\u0447\u043d\u0443\u044e"}},
                    {"value": "email", "label": {"en": "By email only", "id": "Hanya via email", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043f\u043e email"}},
                    {"value": "phone", "label": {"en": "Phone call", "id": "Panggilan telepon", "ru": "\u041f\u043e \u0442\u0435\u043b\u0435\u0444\u043e\u043d\u0443"}},
                ],
            },
            {
                "id": "q2",
                "question": {"en": "What status means a position is waiting for a recipe?", "id": "Status apa yang berarti posisi menunggu resep?", "ru": "\u041a\u0430\u043a\u043e\u0439 \u0441\u0442\u0430\u0442\u0443\u0441 \u043e\u0437\u043d\u0430\u0447\u0430\u0435\u0442 \u043e\u0436\u0438\u0434\u0430\u043d\u0438\u0435 \u0440\u0435\u0446\u0435\u043f\u0442\u0430?"},
                "options": [
                    {"value": "awaiting_recipe", "label": {"en": "awaiting_recipe", "id": "awaiting_recipe", "ru": "awaiting_recipe"}},
                    {"value": "new", "label": {"en": "new", "id": "new", "ru": "new"}},
                    {"value": "scheduled", "label": {"en": "scheduled", "id": "scheduled", "ru": "scheduled"}},
                ],
            },
            {
                "id": "q3",
                "question": {"en": "How many possible statuses does a position have?", "id": "Berapa banyak status yang mungkin dimiliki posisi?", "ru": "\u0421\u043a\u043e\u043b\u044c\u043a\u043e \u0441\u0442\u0430\u0442\u0443\u0441\u043e\u0432 \u043c\u043e\u0436\u0435\u0442 \u0438\u043c\u0435\u0442\u044c \u043f\u043e\u0437\u0438\u0446\u0438\u044f?"},
                "options": [
                    {"value": "12_statuses", "label": {"en": "12+ statuses in the full lifecycle", "id": "12+ status dalam siklus hidup penuh", "ru": "12+ \u0441\u0442\u0430\u0442\u0443\u0441\u043e\u0432 \u0432 \u043f\u043e\u043b\u043d\u043e\u043c \u0446\u0438\u043a\u043b\u0435"}},
                    {"value": "3_statuses", "label": {"en": "3: new, in progress, done", "id": "3: baru, dalam proses, selesai", "ru": "3: \u043d\u043e\u0432\u044b\u0439, \u0432 \u0440\u0430\u0431\u043e\u0442\u0435, \u0433\u043e\u0442\u043e\u0432"}},
                    {"value": "5_statuses", "label": {"en": "5 statuses", "id": "5 status", "ru": "5 \u0441\u0442\u0430\u0442\u0443\u0441\u043e\u0432"}},
                ],
            },
            {
                "id": "q4",
                "question": {"en": "What scheduling method does PMS use?", "id": "Metode penjadwalan apa yang digunakan PMS?", "ru": "\u041a\u0430\u043a\u043e\u0439 \u043c\u0435\u0442\u043e\u0434 \u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442 PMS?"},
                "options": [
                    {"value": "backward_scheduling", "label": {"en": "Backward scheduling from deadline", "id": "Penjadwalan mundur dari tenggat waktu", "ru": "\u041e\u0431\u0440\u0430\u0442\u043d\u043e\u0435 \u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u043e\u0442 \u0434\u0435\u0434\u043b\u0430\u0439\u043d\u0430"}},
                    {"value": "forward", "label": {"en": "Forward scheduling from today", "id": "Penjadwalan maju dari hari ini", "ru": "\u041f\u0440\u044f\u043c\u043e\u0435 \u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u043e\u0442 \u0441\u0435\u0433\u043e\u0434\u043d\u044f"}},
                    {"value": "random", "label": {"en": "Random assignment", "id": "Penugasan acak", "ru": "\u0421\u043b\u0443\u0447\u0430\u0439\u043d\u043e\u0435 \u043d\u0430\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435"}},
                ],
            },
        ],
    },
    "materials": {
        "icon": "\U0001f9f1",
        "title": {"en": "Materials & Stock", "id": "Material & Stok", "ru": "\u041c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b \u0438 \u0441\u043a\u043b\u0430\u0434"},
        "slides": [
            {"title": {"en": "Material Types", "id": "Jenis Material", "ru": "\u0422\u0438\u043f\u044b \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432"}, "content": {"en": "Materials include: glazes, engobes, stencils, raw stone, packaging. Each has a current stock level measured in kg. When stock drops below minimum balance, the system creates an alert. You can set minimum balance per material.", "id": "Material meliputi: glasir, engobe, stensil, batu mentah, kemasan. Masing-masing memiliki level stok saat ini dalam kg.", "ru": "\u041c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b: \u0433\u043b\u0430\u0437\u0443\u0440\u0438, \u044d\u043d\u0433\u043e\u0431\u044b, \u0442\u0440\u0430\u0444\u0430\u0440\u0435\u0442\u044b, \u0441\u044b\u0440\u043e\u0439 \u043a\u0430\u043c\u0435\u043d\u044c, \u0443\u043f\u0430\u043a\u043e\u0432\u043a\u0430. \u041a\u0430\u0436\u0434\u044b\u0439 \u0438\u043c\u0435\u0435\u0442 \u0442\u0435\u043a\u0443\u0449\u0438\u0439 \u0441\u0442\u043e\u043a \u0432 \u043a\u0433. \u041f\u0440\u0438 \u043f\u0430\u0434\u0435\u043d\u0438\u0438 \u043d\u0438\u0436\u0435 \u043c\u0438\u043d\u0438\u043c\u0443\u043c\u0430 \u2014 \u0430\u043b\u0435\u0440\u0442."}, "icon": "\U0001f3a8"},
            {"title": {"en": "Reservations & Consumption", "id": "Reservasi & Konsumsi", "ru": "\u0420\u0435\u0437\u0435\u0440\u0432\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0438 \u0440\u0430\u0441\u0445\u043e\u0434"}, "content": {"en": "When an order is scheduled, materials are RESERVED - they're still in stock but earmarked for that order. When production actually uses them, they're CONSUMED. If insufficient material: status becomes 'insufficient_materials' and a blocking task is created.", "id": "Ketika pesanan dijadwalkan, material DIRESERVASI - masih di stok tapi dicadangkan untuk pesanan itu. Ketika produksi menggunakannya, material DIKONSUMSI.", "ru": "\u041f\u0440\u0438 \u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0438 \u0437\u0430\u043a\u0430\u0437\u0430 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b \u0420\u0415\u0417\u0415\u0420\u0412\u0418\u0420\u0423\u042e\u0422\u0421\u042f. \u041f\u0440\u0438 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u0438\u0438 \u2014 \u0421\u041f\u0418\u0421\u042b\u0412\u0410\u042e\u0422\u0421\u042f. \u0415\u0441\u043b\u0438 \u043d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e \u2014 \u0441\u043e\u0437\u0434\u0430\u0451\u0442\u0441\u044f \u0431\u043b\u043e\u043a\u0438\u0440\u0443\u044e\u0449\u0430\u044f \u0437\u0430\u0434\u0430\u0447\u0430."}, "icon": "\U0001f4e6"},
            {"title": {"en": "Purchase Requests", "id": "Permintaan Pembelian", "ru": "\u0417\u0430\u044f\u0432\u043a\u0438 \u043d\u0430 \u0437\u0430\u043a\u0443\u043f\u043a\u0443"}, "content": {"en": "When material is insufficient, create a purchase request. This goes to the Purchaser role. They find suppliers, get quotes, and order. Track status: pending -> approved -> ordered -> in_transit -> received.", "id": "Ketika material tidak cukup, buat permintaan pembelian. Ini dikirim ke peran Purchaser. Mereka mencari supplier, mendapatkan penawaran, dan memesan.", "ru": "\u041f\u0440\u0438 \u043d\u0435\u0445\u0432\u0430\u0442\u043a\u0435 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u0430 \u0441\u043e\u0437\u0434\u0430\u0439\u0442\u0435 \u0437\u0430\u044f\u0432\u043a\u0443 \u043d\u0430 \u0437\u0430\u043a\u0443\u043f\u043a\u0443. \u041e\u043d\u0430 \u0438\u0434\u0451\u0442 \u0437\u0430\u043a\u0443\u043f\u0449\u0438\u043a\u0443. \u0421\u0442\u0430\u0442\u0443\u0441\u044b: pending -> approved -> ordered -> in_transit -> received."}, "icon": "\U0001f6d2"},
            {"title": {"en": "Min Balance & Alerts", "id": "Saldo Minimum & Peringatan", "ru": "\u041c\u0438\u043d\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 \u0431\u0430\u043b\u0430\u043d\u0441 \u0438 \u0430\u043b\u0435\u0440\u0442\u044b"}, "content": {"en": "Set minimum balance for critical materials. When stock drops below this level, you get a Telegram notification and a dashboard alert. You can override the min balance per material as PM. Smart alerts prevent production stops.", "id": "Tetapkan saldo minimum untuk material kritis. Ketika stok turun di bawah level ini, Anda mendapat notifikasi Telegram dan peringatan dashboard.", "ru": "\u0423\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0435 \u043c\u0438\u043d\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 \u0431\u0430\u043b\u0430\u043d\u0441 \u0434\u043b\u044f \u043a\u0440\u0438\u0442\u0438\u0447\u043d\u044b\u0445 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432. \u041f\u0440\u0438 \u043f\u0430\u0434\u0435\u043d\u0438\u0438 \u043d\u0438\u0436\u0435 \u2014 \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0435 \u0432 Telegram \u0438 \u0430\u043b\u0435\u0440\u0442 \u043d\u0430 \u0434\u0430\u0448\u0431\u043e\u0440\u0434\u0435."}, "icon": "\u26a0\ufe0f"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What happens to materials when an order is scheduled?", "id": "Apa yang terjadi pada material ketika pesanan dijadwalkan?", "ru": "\u0427\u0442\u043e \u043f\u0440\u043e\u0438\u0441\u0445\u043e\u0434\u0438\u0442 \u0441 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u0430\u043c\u0438 \u043f\u0440\u0438 \u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0438 \u0437\u0430\u043a\u0430\u0437\u0430?"}, "options": [
                {"value": "reserved", "label": {"en": "They are reserved", "id": "Mereka direservasi", "ru": "\u041e\u043d\u0438 \u0440\u0435\u0437\u0435\u0440\u0432\u0438\u0440\u0443\u044e\u0442\u0441\u044f"}},
                {"value": "consumed", "label": {"en": "They are consumed immediately", "id": "Mereka dikonsumsi segera", "ru": "\u041e\u043d\u0438 \u0441\u0440\u0430\u0437\u0443 \u0441\u043f\u0438\u0441\u044b\u0432\u0430\u044e\u0442\u0441\u044f"}},
                {"value": "nothing", "label": {"en": "Nothing happens", "id": "Tidak terjadi apa-apa", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e"}},
            ]},
            {"id": "q2", "question": {"en": "What should you do when material is insufficient?", "id": "Apa yang harus Anda lakukan ketika material tidak cukup?", "ru": "\u0427\u0442\u043e \u0434\u0435\u043b\u0430\u0442\u044c \u043f\u0440\u0438 \u043d\u0435\u0445\u0432\u0430\u0442\u043a\u0435 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u0430?"}, "options": [
                {"value": "create_purchase_request", "label": {"en": "Create a purchase request", "id": "Buat permintaan pembelian", "ru": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0437\u0430\u044f\u0432\u043a\u0443 \u043d\u0430 \u0437\u0430\u043a\u0443\u043f\u043a\u0443"}},
                {"value": "wait", "label": {"en": "Wait and hope", "id": "Tunggu dan berharap", "ru": "\u0416\u0434\u0430\u0442\u044c"}},
                {"value": "cancel_order", "label": {"en": "Cancel the order", "id": "Batalkan pesanan", "ru": "\u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c \u0437\u0430\u043a\u0430\u0437"}},
            ]},
            {"id": "q3", "question": {"en": "In what unit is material stock measured?", "id": "Dalam satuan apa stok material diukur?", "ru": "\u0412 \u043a\u0430\u043a\u0438\u0445 \u0435\u0434\u0438\u043d\u0438\u0446\u0430\u0445 \u0438\u0437\u043c\u0435\u0440\u044f\u0435\u0442\u0441\u044f \u0441\u0442\u043e\u043a?"}, "options": [
                {"value": "kg", "label": {"en": "Kilograms (kg)", "id": "Kilogram (kg)", "ru": "\u041a\u0438\u043b\u043e\u0433\u0440\u0430\u043c\u043c\u044b (\u043a\u0433)"}},
                {"value": "pieces", "label": {"en": "Pieces", "id": "Buah", "ru": "\u0428\u0442\u0443\u043a\u0438"}},
                {"value": "liters", "label": {"en": "Liters", "id": "Liter", "ru": "\u041b\u0438\u0442\u0440\u044b"}},
            ]},
            {"id": "q4", "question": {"en": "What triggers a material alert?", "id": "Apa yang memicu peringatan material?", "ru": "\u0427\u0442\u043e \u0432\u044b\u0437\u044b\u0432\u0430\u0435\u0442 \u0430\u043b\u0435\u0440\u0442 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432?"}, "options": [
                {"value": "min_balance", "label": {"en": "Stock drops below minimum balance", "id": "Stok turun di bawah saldo minimum", "ru": "\u0421\u0442\u043e\u043a \u043f\u0430\u0434\u0430\u0435\u0442 \u043d\u0438\u0436\u0435 \u043c\u0438\u043d\u0438\u043c\u0430\u043b\u044c\u043d\u043e\u0433\u043e \u0431\u0430\u043b\u0430\u043d\u0441\u0430"}},
                {"value": "new_order", "label": {"en": "Every new order", "id": "Setiap pesanan baru", "ru": "\u041a\u0430\u0436\u0434\u044b\u0439 \u043d\u043e\u0432\u044b\u0439 \u0437\u0430\u043a\u0430\u0437"}},
                {"value": "manual", "label": {"en": "Only when you manually check", "id": "Hanya saat Anda periksa manual", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043f\u0440\u0438 \u0440\u0443\u0447\u043d\u043e\u0439 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0435"}},
            ]},
        ],
    },
    "schedule": {
        "icon": "\U0001f4c5",
        "title": {"en": "Production Schedule", "id": "Jadwal Produksi", "ru": "\u0420\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u0430"},
        "slides": [
            {"title": {"en": "FIFO Scheduling", "id": "Penjadwalan FIFO", "ru": "FIFO-\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435"}, "content": {"en": "Orders are processed First In, First Out by default. The earliest deadline gets priority. The scheduler assigns production slots automatically based on available capacity and kiln schedule.", "id": "Pesanan diproses First In, First Out secara default. Tenggat waktu paling awal mendapat prioritas.", "ru": "\u0417\u0430\u043a\u0430\u0437\u044b \u043e\u0431\u0440\u0430\u0431\u0430\u0442\u044b\u0432\u0430\u044e\u0442\u0441\u044f \u043f\u043e FIFO. \u0421\u0430\u043c\u044b\u0439 \u0440\u0430\u043d\u043d\u0438\u0439 \u0434\u0435\u0434\u043b\u0430\u0439\u043d \u2014 \u043f\u0440\u0438\u043e\u0440\u0438\u0442\u0435\u0442. \u041f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0449\u0438\u043a \u043d\u0430\u0437\u043d\u0430\u0447\u0430\u0435\u0442 \u0441\u043b\u043e\u0442\u044b \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438."}, "icon": "\U0001f4cb"},
            {"title": {"en": "Kiln as Constraint (TOC)", "id": "Kiln sebagai Kendala (TOC)", "ru": "\u041f\u0435\u0447\u044c \u043a\u0430\u043a \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u0435 (TOC)"}, "content": {"en": "The kiln is the bottleneck. Everything else is scheduled around kiln availability. TOC (Theory of Constraints) means: maximize kiln utilization, never let kilns sit idle. Batch fill optimization ensures minimum wasted space.", "id": "Kiln adalah bottleneck. Semua dijadwalkan berdasarkan ketersediaan kiln. TOC berarti: maksimalkan utilisasi kiln.", "ru": "\u041f\u0435\u0447\u044c \u2014 \u0431\u0443\u0442\u044b\u043b\u043e\u0447\u043d\u043e\u0435 \u0433\u043e\u0440\u043b\u043e. \u0412\u0441\u0451 \u043f\u043b\u0430\u043d\u0438\u0440\u0443\u0435\u0442\u0441\u044f \u0432\u043e\u043a\u0440\u0443\u0433 \u043f\u0435\u0447\u0438. TOC: \u043c\u0430\u043a\u0441\u0438\u043c\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0443, \u043d\u0435 \u0434\u043e\u043f\u0443\u0441\u043a\u0430\u0442\u044c \u043f\u0440\u043e\u0441\u0442\u043e\u044f."}, "icon": "\U0001f525"},
            {"title": {"en": "Schedule View", "id": "Tampilan Jadwal", "ru": "\u0412\u0438\u0434 \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u044f"}, "content": {"en": "The Schedule page shows a timeline view of all positions grouped by production stage. Color-coded cards show progress. You can drag to reschedule, click for details. The system auto-recalculates downstream dates when you change anything.", "id": "Halaman Jadwal menampilkan tampilan timeline semua posisi dikelompokkan berdasarkan tahap produksi.", "ru": "\u0421\u0442\u0440\u0430\u043d\u0438\u0446\u0430 \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u044f \u043f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442 \u0442\u0430\u0439\u043c\u043b\u0430\u0439\u043d \u0432\u0441\u0435\u0445 \u043f\u043e\u0437\u0438\u0446\u0438\u0439 \u043f\u043e \u044d\u0442\u0430\u043f\u0430\u043c. \u0426\u0432\u0435\u0442\u043e\u0432\u044b\u0435 \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0438 \u043f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u044e\u0442 \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441."}, "icon": "\U0001f5d3\ufe0f"},
            {"title": {"en": "Rescheduling", "id": "Penjadwalan Ulang", "ru": "\u041f\u0435\u0440\u0435\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435"}, "content": {"en": "When something changes (material delay, kiln breakdown, priority shift), the system can recalculate the entire schedule. The auto-reschedule feature propagates changes through all affected positions and notifies the team.", "id": "Ketika sesuatu berubah, sistem dapat menghitung ulang seluruh jadwal.", "ru": "\u041a\u043e\u0433\u0434\u0430 \u0447\u0442\u043e-\u0442\u043e \u043c\u0435\u043d\u044f\u0435\u0442\u0441\u044f, \u0441\u0438\u0441\u0442\u0435\u043c\u0430 \u043f\u0435\u0440\u0435\u0441\u0447\u0438\u0442\u044b\u0432\u0430\u0435\u0442 \u0432\u0441\u0451 \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435. \u0410\u0432\u0442\u043e-\u043f\u0435\u0440\u0435\u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u043f\u0440\u043e\u043f\u0430\u0433\u0438\u0440\u0443\u0435\u0442 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0438 \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u044f\u0435\u0442 \u043a\u043e\u043c\u0430\u043d\u0434\u0443."}, "icon": "\U0001f504"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What scheduling method is used by default?", "id": "Metode penjadwalan apa yang digunakan secara default?", "ru": "\u041a\u0430\u043a\u043e\u0439 \u043c\u0435\u0442\u043e\u0434 \u043f\u043b\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442\u0441\u044f \u043f\u043e \u0443\u043c\u043e\u043b\u0447\u0430\u043d\u0438\u044e?"}, "options": [
                {"value": "fifo", "label": {"en": "FIFO (First In, First Out)", "id": "FIFO", "ru": "FIFO"}},
                {"value": "lifo", "label": {"en": "LIFO (Last In, First Out)", "id": "LIFO", "ru": "LIFO"}},
                {"value": "random", "label": {"en": "Random", "id": "Acak", "ru": "\u0421\u043b\u0443\u0447\u0430\u0439\u043d\u044b\u0439"}},
            ]},
            {"id": "q2", "question": {"en": "What is the production bottleneck?", "id": "Apa bottleneck produksi?", "ru": "\u0427\u0442\u043e \u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u0431\u0443\u0442\u044b\u043b\u043e\u0447\u043d\u044b\u043c \u0433\u043e\u0440\u043b\u043e\u043c?"}, "options": [
                {"value": "kiln", "label": {"en": "The kiln", "id": "Kiln", "ru": "\u041f\u0435\u0447\u044c"}},
                {"value": "glazing", "label": {"en": "Glazing station", "id": "Stasiun glasir", "ru": "\u0413\u043b\u0430\u0437\u0443\u0440\u043e\u0432\u043a\u0430"}},
                {"value": "packaging", "label": {"en": "Packaging", "id": "Pengemasan", "ru": "\u0423\u043f\u0430\u043a\u043e\u0432\u043a\u0430"}},
            ]},
            {"id": "q3", "question": {"en": "What direction does the scheduler plan from?", "id": "Dari arah mana scheduler merencanakan?", "ru": "\u0412 \u043a\u0430\u043a\u043e\u043c \u043d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0438 \u043f\u043b\u0430\u043d\u0438\u0440\u0443\u0435\u0442 \u0441\u0438\u0441\u0442\u0435\u043c\u0430?"}, "options": [
                {"value": "backward", "label": {"en": "Backward from deadline", "id": "Mundur dari tenggat", "ru": "\u041d\u0430\u0437\u0430\u0434 \u043e\u0442 \u0434\u0435\u0434\u043b\u0430\u0439\u043d\u0430"}},
                {"value": "forward", "label": {"en": "Forward from today", "id": "Maju dari hari ini", "ru": "\u0412\u043f\u0435\u0440\u0451\u0434 \u043e\u0442 \u0441\u0435\u0433\u043e\u0434\u043d\u044f"}},
                {"value": "middle", "label": {"en": "From the middle", "id": "Dari tengah", "ru": "\u041e\u0442 \u0441\u0435\u0440\u0435\u0434\u0438\u043d\u044b"}},
            ]},
            {"id": "q4", "question": {"en": "What happens when you change the schedule?", "id": "Apa yang terjadi saat Anda mengubah jadwal?", "ru": "\u0427\u0442\u043e \u043f\u0440\u043e\u0438\u0441\u0445\u043e\u0434\u0438\u0442 \u043f\u0440\u0438 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0438 \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u044f?"}, "options": [
                {"value": "auto_reschedule", "label": {"en": "System auto-recalculates all affected positions", "id": "Sistem otomatis menghitung ulang semua posisi terpengaruh", "ru": "\u0421\u0438\u0441\u0442\u0435\u043c\u0430 \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438 \u043f\u0435\u0440\u0435\u0441\u0447\u0438\u0442\u044b\u0432\u0430\u0435\u0442 \u0432\u0441\u0435 \u0437\u0430\u0442\u0440\u043e\u043d\u0443\u0442\u044b\u0435 \u043f\u043e\u0437\u0438\u0446\u0438\u0438"}},
                {"value": "nothing", "label": {"en": "Nothing, manual only", "id": "Tidak ada, hanya manual", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e, \u0442\u043e\u043b\u044c\u043a\u043e \u0432\u0440\u0443\u0447\u043d\u0443\u044e"}},
                {"value": "reset", "label": {"en": "All schedules are reset", "id": "Semua jadwal direset", "ru": "\u0412\u0441\u0435 \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u044f \u0441\u0431\u0440\u0430\u0441\u044b\u0432\u0430\u044e\u0442\u0441\u044f"}},
            ]},
        ],
    },
    "kilns": {
        "icon": "\U0001f525",
        "title": {"en": "Kilns & Firing", "id": "Kiln & Pembakaran", "ru": "\u041f\u0435\u0447\u0438 \u0438 \u043e\u0431\u0436\u0438\u0433"},
        "slides": [
            {"title": {"en": "Kiln Types & Capacity", "id": "Jenis & Kapasitas Kiln", "ru": "\u0422\u0438\u043f\u044b \u043f\u0435\u0447\u0435\u0439 \u0438 \u0451\u043c\u043a\u043e\u0441\u0442\u044c"}, "content": {"en": "Each kiln has a max temperature and capacity in sqm. Zone-based loading: edge zone (vertical, for larger tiles) and flat zone (horizontal). The scheduler optimizes batch fill to maximize utilization.", "id": "Setiap kiln memiliki suhu maksimum dan kapasitas dalam sqm.", "ru": "\u0423 \u043a\u0430\u0436\u0434\u043e\u0439 \u043f\u0435\u0447\u0438 \u0435\u0441\u0442\u044c \u043c\u0430\u043a\u0441. \u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430 \u0438 \u0451\u043c\u043a\u043e\u0441\u0442\u044c \u0432 sqm. \u0417\u043e\u043d\u043d\u0430\u044f \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0430: \u0440\u0435\u0431\u0440\u043e\u0432\u0430\u044f (\u0434\u043b\u044f \u043a\u0440\u0443\u043f\u043d\u044b\u0445) \u0438 \u043f\u043b\u043e\u0441\u043a\u0430\u044f."}, "icon": "\U0001f3ed"},
            {"title": {"en": "Inspections", "id": "Inspeksi", "ru": "\u0418\u043d\u0441\u043f\u0435\u043a\u0446\u0438\u0438"}, "content": {"en": "Weekly kiln inspections track condition: heating elements, thermocouple accuracy, door seal, shelf condition. Log issues to plan maintenance proactively.", "id": "Inspeksi kiln mingguan melacak kondisi: elemen pemanas, akurasi thermocouple, segel pintu, kondisi rak.", "ru": "\u0415\u0436\u0435\u043d\u0435\u0434\u0435\u043b\u044c\u043d\u044b\u0435 \u0438\u043d\u0441\u043f\u0435\u043a\u0446\u0438\u0438 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u044e\u0442 \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435: \u043d\u0430\u0433\u0440\u0435\u0432\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0435 \u044d\u043b\u0435\u043c\u0435\u043d\u0442\u044b, \u0442\u0435\u0440\u043c\u043e\u043f\u0430\u0440\u0430, \u0443\u043f\u043b\u043e\u0442\u043d\u0438\u0442\u0435\u043b\u044c \u0434\u0432\u0435\u0440\u0438, \u043f\u043e\u043b\u043a\u0438."}, "icon": "\U0001f50d"},
            {"title": {"en": "Kiln Shelves", "id": "Rak Kiln", "ru": "\u041f\u043e\u043b\u043a\u0438 \u043f\u0435\u0447\u0435\u0439"}, "content": {"en": "Kiln shelves have a lifecycle: SiC (200 cycles), Cordierite (150), Mullite (300), Alumina (250). Track cycle count per shelf. When shelves near end-of-life, the system creates replacement tasks and logs OPEX.", "id": "Rak kiln memiliki siklus hidup. Lacak jumlah siklus per rak.", "ru": "\u041f\u043e\u043b\u043a\u0438 \u0438\u043c\u0435\u044e\u0442 \u0436\u0438\u0437\u043d\u0435\u043d\u043d\u044b\u0439 \u0446\u0438\u043a\u043b. \u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0439\u0442\u0435 \u0446\u0438\u043a\u043b\u044b \u043a\u0430\u0436\u0434\u043e\u0439 \u043f\u043e\u043b\u043a\u0438. \u041f\u0440\u0438 \u0438\u0437\u043d\u043e\u0441\u0435 \u2014 \u0437\u0430\u0434\u0430\u0447\u0430 \u043d\u0430 \u0437\u0430\u043c\u0435\u043d\u0443 + OPEX."}, "icon": "\U0001f6e0\ufe0f"},
            {"title": {"en": "Firing Profiles", "id": "Profil Pembakaran", "ru": "\u041f\u0440\u043e\u0444\u0438\u043b\u0438 \u043e\u0431\u0436\u0438\u0433\u0430"}, "content": {"en": "Each product type has a firing profile: temperature stages (ramp up, soak, cool down), total duration, target temperature. Multi-round firing for special products. Temperature logs record actual readings per batch.", "id": "Setiap jenis produk memiliki profil pembakaran: tahap suhu, durasi total.", "ru": "\u0423 \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u043f\u0440\u043e\u0434\u0443\u043a\u0442\u0430 \u2014 \u043f\u0440\u043e\u0444\u0438\u043b\u044c \u043e\u0431\u0436\u0438\u0433\u0430: \u044d\u0442\u0430\u043f\u044b \u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u044b, \u0434\u043b\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0441\u0442\u044c, \u0446\u0435\u043b\u0435\u0432\u0430\u044f \u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430."}, "icon": "\U0001f321\ufe0f"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What determines which kiln to use for a batch?", "id": "Apa yang menentukan kiln mana yang digunakan?", "ru": "\u0427\u0442\u043e \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u044f\u0435\u0442 \u0432\u044b\u0431\u043e\u0440 \u043f\u0435\u0447\u0438 \u0434\u043b\u044f \u043f\u0430\u0440\u0442\u0438\u0438?"}, "options": [
                {"value": "temperature_and_capacity", "label": {"en": "Temperature compatibility and capacity", "id": "Kompatibilitas suhu dan kapasitas", "ru": "\u0421\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u043e\u0441\u0442\u044c \u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u044b \u0438 \u0451\u043c\u043a\u043e\u0441\u0442\u044c"}},
                {"value": "random", "label": {"en": "Random", "id": "Acak", "ru": "\u0421\u043b\u0443\u0447\u0430\u0439\u043d\u043e"}},
                {"value": "alphabetical", "label": {"en": "Alphabetical order", "id": "Urutan abjad", "ru": "\u041f\u043e \u0430\u043b\u0444\u0430\u0432\u0438\u0442\u0443"}},
            ]},
            {"id": "q2", "question": {"en": "How often should kiln inspections be done?", "id": "Seberapa sering inspeksi kiln harus dilakukan?", "ru": "\u041a\u0430\u043a \u0447\u0430\u0441\u0442\u043e \u043d\u0443\u0436\u043d\u043e \u0434\u0435\u043b\u0430\u0442\u044c \u0438\u043d\u0441\u043f\u0435\u043a\u0446\u0438\u0438?"}, "options": [
                {"value": "weekly", "label": {"en": "Weekly", "id": "Mingguan", "ru": "\u0415\u0436\u0435\u043d\u0435\u0434\u0435\u043b\u044c\u043d\u043e"}},
                {"value": "monthly", "label": {"en": "Monthly", "id": "Bulanan", "ru": "\u0415\u0436\u0435\u043c\u0435\u0441\u044f\u0447\u043d\u043e"}},
                {"value": "yearly", "label": {"en": "Yearly", "id": "Tahunan", "ru": "\u0415\u0436\u0435\u0433\u043e\u0434\u043d\u043e"}},
            ]},
            {"id": "q3", "question": {"en": "Why do we track kiln shelf cycles?", "id": "Mengapa kita melacak siklus rak kiln?", "ru": "\u0417\u0430\u0447\u0435\u043c \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0442\u044c \u0446\u0438\u043a\u043b\u044b \u043f\u043e\u043b\u043e\u043a?"}, "options": [
                {"value": "cycles_tracking", "label": {"en": "To replace shelves before they fail", "id": "Untuk mengganti rak sebelum rusak", "ru": "\u0427\u0442\u043e\u0431\u044b \u0437\u0430\u043c\u0435\u043d\u0438\u0442\u044c \u043f\u043e\u043b\u043a\u0438 \u0434\u043e \u043f\u043e\u043b\u043e\u043c\u043a\u0438"}},
                {"value": "for_fun", "label": {"en": "Just for statistics", "id": "Hanya untuk statistik", "ru": "\u041f\u0440\u043e\u0441\u0442\u043e \u0434\u043b\u044f \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0438"}},
                {"value": "not_needed", "label": {"en": "It's not needed", "id": "Tidak diperlukan", "ru": "\u042d\u0442\u043e \u043d\u0435 \u043d\u0443\u0436\u043d\u043e"}},
            ]},
            {"id": "q4", "question": {"en": "What shelf material has the longest lifecycle?", "id": "Material rak mana yang paling tahan lama?", "ru": "\u041a\u0430\u043a\u043e\u0439 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b \u043f\u043e\u043b\u043e\u043a \u0441\u0430\u043c\u044b\u0439 \u0434\u043e\u043b\u0433\u043e\u0432\u0435\u0447\u043d\u044b\u0439?"}, "options": [
                {"value": "sic", "label": {"en": "SiC (200 cycles)", "id": "SiC (200 siklus)", "ru": "SiC (200 \u0446\u0438\u043a\u043b\u043e\u0432)"}},
                {"value": "mullite", "label": {"en": "Mullite (300 cycles)", "id": "Mullite (300 siklus)", "ru": "\u041c\u0443\u043b\u043b\u0438\u0442 (300 \u0446\u0438\u043a\u043b\u043e\u0432)"}},
                {"value": "cordierite", "label": {"en": "Cordierite (150 cycles)", "id": "Cordierite (150 siklus)", "ru": "\u041a\u043e\u0440\u0434\u0438\u0435\u0440\u0438\u0442 (150 \u0446\u0438\u043a\u043b\u043e\u0432)"}},
            ]},
        ],
    },
    "quality": {
        "icon": "\u2705",
        "title": {"en": "Quality Control", "id": "Kontrol Kualitas", "ru": "\u041a\u043e\u043d\u0442\u0440\u043e\u043b\u044c \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430"},
        "slides": [
            {"title": {"en": "Two QC Stages", "id": "Dua Tahap QC", "ru": "\u0414\u0432\u0430 \u044d\u0442\u0430\u043f\u0430 QC"}, "content": {"en": "Pre-Kiln QC: check before firing (engobe coverage, glaze uniformity, no cracks). Final QC: check after firing (color accuracy, no defects, correct dimensions). Both use digital checklists.", "id": "Pre-Kiln QC: periksa sebelum pembakaran. Final QC: periksa setelah pembakaran. Keduanya menggunakan checklist digital.", "ru": "Pre-Kiln QC: \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0434\u043e \u043e\u0431\u0436\u0438\u0433\u0430. Final QC: \u043f\u043e\u0441\u043b\u0435 \u043e\u0431\u0436\u0438\u0433\u0430. \u041e\u0431\u0430 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u044e\u0442 \u0446\u0438\u0444\u0440\u043e\u0432\u044b\u0435 \u0447\u0435\u043a-\u043b\u0438\u0441\u0442\u044b."}, "icon": "\U0001f50d"},
            {"title": {"en": "Pre-Kiln Stages", "id": "Tahap Sebelum Kiln", "ru": "\u042d\u0442\u0430\u043f\u044b \u0434\u043e \u043e\u0431\u0436\u0438\u0433\u0430"}, "content": {"en": "5 stages before firing: 1) Unpacking stone 2) Engobe application 3) Glazing 4) Drying 5) Edge cleaning. Each stage has speed metrics and quality checkpoints.", "id": "5 tahap sebelum pembakaran: 1) Bongkar batu 2) Engobe 3) Glasir 4) Pengeringan 5) Pembersihan tepi.", "ru": "5 \u044d\u0442\u0430\u043f\u043e\u0432 \u0434\u043e \u043e\u0431\u0436\u0438\u0433\u0430: 1) \u0420\u0430\u0441\u043f\u0430\u043a\u043e\u0432\u043a\u0430 2) \u042d\u043d\u0433\u043e\u0431 3) \u0413\u043b\u0430\u0437\u0443\u0440\u043e\u0432\u043a\u0430 4) \u0421\u0443\u0448\u043a\u0430 5) \u041e\u0447\u0438\u0441\u0442\u043a\u0430 \u043a\u0440\u0430\u0451\u0432."}, "icon": "\U0001f4dd"},
            {"title": {"en": "Defect Handling", "id": "Penanganan Cacat", "ru": "\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u0434\u0435\u0444\u0435\u043a\u0442\u043e\u0432"}, "content": {"en": "Defects found during QC: log type, severity, photo. Options: grinding (polish surface), refire (fire again), scrap. Defect coefficient matrix considers glaze type + product type for expected defect rate.", "id": "Cacat ditemukan selama QC: catat jenis, tingkat keparahan, foto. Opsi: grinding, refire, scrap.", "ru": "\u0414\u0435\u0444\u0435\u043a\u0442\u044b \u043f\u0440\u0438 QC: \u0442\u0438\u043f, \u0441\u0442\u0435\u043f\u0435\u043d\u044c, \u0444\u043e\u0442\u043e. \u041e\u043f\u0446\u0438\u0438: \u0448\u043b\u0438\u0444\u043e\u0432\u043a\u0430, \u043f\u0435\u0440\u0435\u043e\u0431\u0436\u0438\u0433, \u0431\u0440\u0430\u043a."}, "icon": "\u26a0\ufe0f"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What are the two QC stages?", "id": "Apa dua tahap QC?", "ru": "\u041a\u0430\u043a\u0438\u0435 \u0434\u0432\u0430 \u044d\u0442\u0430\u043f\u0430 QC?"}, "options": [
                {"value": "pre_kiln_final", "label": {"en": "Pre-Kiln QC and Final QC", "id": "Pre-Kiln QC dan Final QC", "ru": "Pre-Kiln QC \u0438 Final QC"}},
                {"value": "visual_lab", "label": {"en": "Visual and Lab testing", "id": "Visual dan Lab testing", "ru": "\u0412\u0438\u0437\u0443\u0430\u043b\u044c\u043d\u044b\u0439 \u0438 \u043b\u0430\u0431\u043e\u0440\u0430\u0442\u043e\u0440\u043d\u044b\u0439"}},
                {"value": "none", "label": {"en": "There is only one QC", "id": "Hanya ada satu QC", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043e\u0434\u0438\u043d QC"}},
            ]},
            {"id": "q2", "question": {"en": "How many stages before firing?", "id": "Berapa tahap sebelum pembakaran?", "ru": "\u0421\u043a\u043e\u043b\u044c\u043a\u043e \u044d\u0442\u0430\u043f\u043e\u0432 \u0434\u043e \u043e\u0431\u0436\u0438\u0433\u0430?"}, "options": [
                {"value": "five_stages", "label": {"en": "5 (unpacking, engobe, glazing, drying, edge cleaning)", "id": "5 (bongkar, engobe, glasir, pengeringan, pembersihan tepi)", "ru": "5 (\u0440\u0430\u0441\u043f\u0430\u043a\u043e\u0432\u043a\u0430, \u044d\u043d\u0433\u043e\u0431, \u0433\u043b\u0430\u0437\u0443\u0440\u043e\u0432\u043a\u0430, \u0441\u0443\u0448\u043a\u0430, \u043e\u0447\u0438\u0441\u0442\u043a\u0430)"}},
                {"value": "three", "label": {"en": "3", "id": "3", "ru": "3"}},
                {"value": "seven", "label": {"en": "7", "id": "7", "ru": "7"}},
            ]},
            {"id": "q3", "question": {"en": "What options exist for defective tiles?", "id": "Opsi apa yang ada untuk ubin cacat?", "ru": "\u0427\u0442\u043e \u043c\u043e\u0436\u043d\u043e \u0441\u0434\u0435\u043b\u0430\u0442\u044c \u0441 \u0431\u0440\u0430\u043a\u043e\u0432\u0430\u043d\u043d\u043e\u0439 \u043f\u043b\u0438\u0442\u043a\u043e\u0439?"}, "options": [
                {"value": "grinding_or_refire", "label": {"en": "Grinding, refire, or scrap", "id": "Grinding, refire, atau scrap", "ru": "\u0428\u043b\u0438\u0444\u043e\u0432\u043a\u0430, \u043f\u0435\u0440\u0435\u043e\u0431\u0436\u0438\u0433 \u0438\u043b\u0438 \u0431\u0440\u0430\u043a"}},
                {"value": "only_scrap", "label": {"en": "Only scrap", "id": "Hanya scrap", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0431\u0440\u0430\u043a"}},
                {"value": "ignore", "label": {"en": "Ship anyway", "id": "Kirim saja", "ru": "\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043a\u0430\u043a \u0435\u0441\u0442\u044c"}},
            ]},
        ],
    },
    "tasks": {
        "icon": "\U0001f4cb",
        "title": {"en": "Tasks & Blocking", "id": "Tugas & Pemblokiran", "ru": "\u0417\u0430\u0434\u0430\u0447\u0438 \u0438 \u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u043a\u0438"},
        "slides": [
            {"title": {"en": "Blocking Tasks", "id": "Tugas Pemblokir", "ru": "\u0411\u043b\u043e\u043a\u0438\u0440\u0443\u044e\u0449\u0438\u0435 \u0437\u0430\u0434\u0430\u0447\u0438"}, "content": {"en": "When a position can't proceed (missing recipe, insufficient materials, needs stencil), a blocking task is auto-created. Production stops for that position until the task is resolved. Your job: resolve these ASAP.", "id": "Ketika posisi tidak bisa dilanjutkan, tugas pemblokir otomatis dibuat.", "ru": "\u041a\u043e\u0433\u0434\u0430 \u043f\u043e\u0437\u0438\u0446\u0438\u044f \u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c\u0441\u044f, \u0441\u043e\u0437\u0434\u0430\u0451\u0442\u0441\u044f \u0431\u043b\u043e\u043a\u0438\u0440\u0443\u044e\u0449\u0430\u044f \u0437\u0430\u0434\u0430\u0447\u0430. \u0412\u0430\u0448\u0430 \u0437\u0430\u0434\u0430\u0447\u0430 \u2014 \u0440\u0435\u0448\u0430\u0442\u044c \u0438\u0445 ASAP."}, "icon": "\U0001f6d1"},
            {"title": {"en": "Force Unblock", "id": "Paksa Buka Blokir", "ru": "\u041f\u0440\u0438\u043d\u0443\u0434\u0438\u0442\u0435\u043b\u044c\u043d\u0430\u044f \u0440\u0430\u0437\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u043a\u0430"}, "content": {"en": "Sometimes you need to override a block (material coming tomorrow, recipe approved verbally). Smart Force Unblock gives you 3 context-aware options per blocking type. Warning: CEO gets notified on every force unblock!", "id": "Kadang Anda perlu override blokir. Smart Force Unblock memberikan 3 opsi sesuai konteks.", "ru": "\u0418\u043d\u043e\u0433\u0434\u0430 \u043d\u0443\u0436\u043d\u043e \u043e\u0431\u043e\u0439\u0442\u0438 \u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u043a\u0443. Smart Force Unblock \u0434\u0430\u0451\u0442 3 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u043d\u044b\u0445 \u043e\u043f\u0446\u0438\u0438. \u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435: CEO \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442 \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0435!"}, "icon": "\U0001f513"},
            {"title": {"en": "Daily Task Management", "id": "Manajemen Tugas Harian", "ru": "\u0415\u0436\u0435\u0434\u043d\u0435\u0432\u043d\u043e\u0435 \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0437\u0430\u0434\u0430\u0447\u0430\u043c\u0438"}, "content": {"en": "Tasks page shows all pending items. Filter by type, priority, status. The Telegram bot sends your morning briefing with prioritized tasks. AI helps prioritize based on deadline impact and blocking chain analysis.", "id": "Halaman tugas menampilkan semua item yang tertunda. Filter berdasarkan jenis, prioritas, status.", "ru": "\u0421\u0442\u0440\u0430\u043d\u0438\u0446\u0430 \u0437\u0430\u0434\u0430\u0447 \u043f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442 \u0432\u0441\u0435 \u043f\u0435\u043d\u0434\u0438\u043d\u0433\u0438. AI \u043f\u043e\u043c\u043e\u0433\u0430\u0435\u0442 \u043f\u0440\u0438\u043e\u0440\u0438\u0442\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043f\u043e \u0432\u043b\u0438\u044f\u043d\u0438\u044e \u043d\u0430 \u0434\u0435\u0434\u043b\u0430\u0439\u043d\u044b."}, "icon": "\U0001f4c8"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What creates a blocking task automatically?", "id": "Apa yang membuat tugas pemblokir otomatis?", "ru": "\u0427\u0442\u043e \u0441\u043e\u0437\u0434\u0430\u0451\u0442 \u0431\u043b\u043e\u043a\u0438\u0440\u0443\u044e\u0449\u0443\u044e \u0437\u0430\u0434\u0430\u0447\u0443 \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438?"}, "options": [
                {"value": "blocking_tasks", "label": {"en": "Missing recipe, insufficient materials, needs stencil", "id": "Resep hilang, material kurang, perlu stensil", "ru": "\u041d\u0435\u0442 \u0440\u0435\u0446\u0435\u043f\u0442\u0430, \u043d\u0435\u0445\u0432\u0430\u0442\u043a\u0430 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432, \u043d\u0443\u0436\u0435\u043d \u0442\u0440\u0430\u0444\u0430\u0440\u0435\u0442"}},
                {"value": "manual", "label": {"en": "Only manual creation", "id": "Hanya dibuat manual", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0432\u0440\u0443\u0447\u043d\u0443\u044e"}},
                {"value": "schedule", "label": {"en": "On a schedule", "id": "Sesuai jadwal", "ru": "\u041f\u043e \u0440\u0430\u0441\u043f\u0438\u0441\u0430\u043d\u0438\u044e"}},
            ]},
            {"id": "q2", "question": {"en": "How do you override a production block?", "id": "Bagaimana cara override blokir produksi?", "ru": "\u041a\u0430\u043a \u043e\u0431\u043e\u0439\u0442\u0438 \u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u043a\u0443?"}, "options": [
                {"value": "force_unblock", "label": {"en": "Use Force Unblock with context-aware options", "id": "Gunakan Force Unblock dengan opsi kontekstual", "ru": "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c Force Unblock \u0441 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u043d\u044b\u043c\u0438 \u043e\u043f\u0446\u0438\u044f\u043c\u0438"}},
                {"value": "delete", "label": {"en": "Delete the task", "id": "Hapus tugas", "ru": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0437\u0430\u0434\u0430\u0447\u0443"}},
                {"value": "ignore", "label": {"en": "Just ignore it", "id": "Abaikan saja", "ru": "\u041f\u0440\u043e\u0438\u0433\u043d\u043e\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c"}},
            ]},
            {"id": "q3", "question": {"en": "Who gets notified when you force unblock?", "id": "Siapa yang diberitahu saat Anda paksa buka blokir?", "ru": "\u041a\u0442\u043e \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442 \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0435 \u043f\u0440\u0438 force unblock?"}, "options": [
                {"value": "ceo_notification", "label": {"en": "CEO via Telegram", "id": "CEO via Telegram", "ru": "CEO \u0447\u0435\u0440\u0435\u0437 Telegram"}},
                {"value": "nobody", "label": {"en": "Nobody", "id": "Tidak ada", "ru": "\u041d\u0438\u043a\u0442\u043e"}},
                {"value": "team", "label": {"en": "The whole team", "id": "Seluruh tim", "ru": "\u0412\u0441\u044f \u043a\u043e\u043c\u0430\u043d\u0434\u0430"}},
            ]},
        ],
    },
    "telegram": {
        "icon": "\U0001f4f1",
        "title": {"en": "Telegram Bot", "id": "Bot Telegram", "ru": "Telegram-\u0431\u043e\u0442"},
        "slides": [
            {"title": {"en": "Morning Briefing", "id": "Briefing Pagi", "ru": "\u0423\u0442\u0440\u0435\u043d\u043d\u0438\u0439 \u0431\u0440\u0438\u0444\u0438\u043d\u0433"}, "content": {"en": "Every morning at 8 AM, the bot sends you a briefing: greeting, yesterday's results, today's tasks, blocking issues, achievements, daily challenge, and quick action buttons.", "id": "Setiap pagi jam 8, bot mengirim briefing: sapaan, hasil kemarin, tugas hari ini, masalah pemblokir.", "ru": "\u041a\u0430\u0436\u0434\u043e\u0435 \u0443\u0442\u0440\u043e \u0432 8:00 \u0431\u043e\u0442 \u0448\u043b\u0451\u0442 \u0431\u0440\u0438\u0444\u0438\u043d\u0433: \u043f\u0440\u0438\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u0435, \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u044b \u0432\u0447\u0435\u0440\u0430, \u0437\u0430\u0434\u0430\u0447\u0438 \u0441\u0435\u0433\u043e\u0434\u043d\u044f, \u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u043a\u0438."}, "icon": "\U0001f305"},
            {"title": {"en": "Photo Verification", "id": "Verifikasi Foto", "ru": "\u0424\u043e\u0442\u043e-\u0432\u0435\u0440\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u044f"}, "content": {"en": "Send a photo of a recipe card to the bot. OCR extracts the data, compares with the recipe spec, calculates accuracy score, and awards points. This is how you earn XP for precision!", "id": "Kirim foto kartu resep ke bot. OCR mengekstrak data, membandingkan dengan spesifikasi, dan memberikan poin.", "ru": "\u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0444\u043e\u0442\u043e \u0440\u0435\u0446\u0435\u043f\u0442\u0443\u0440\u043d\u043e\u0439 \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0438. OCR \u0438\u0437\u0432\u043b\u0435\u0447\u0451\u0442 \u0434\u0430\u043d\u043d\u044b\u0435, \u0441\u0440\u0430\u0432\u043d\u0438\u0442 \u0441\u043e \u0441\u043f\u0435\u043a\u043e\u0439 \u0438 \u043d\u0430\u0447\u0438\u0441\u043b\u0438\u0442 \u043e\u0447\u043a\u0438."}, "icon": "\U0001f4f8"},
            {"title": {"en": "Available Commands", "id": "Perintah yang Tersedia", "ru": "\u0414\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0435 \u043a\u043e\u043c\u0430\u043d\u0434\u044b"}, "content": {"en": "Key commands: /mystats, /leaderboard, /stock, /challenge, /achievements, /points, /cancel_verify. You can also use natural language - the AI understands context!", "id": "Perintah utama: /mystats, /leaderboard, /stock, /challenge. Anda juga bisa menggunakan bahasa alami!", "ru": "\u041a\u043e\u043c\u0430\u043d\u0434\u044b: /mystats, /leaderboard, /stock, /challenge, /achievements, /points. \u041c\u043e\u0436\u043d\u043e \u043f\u0438\u0441\u0430\u0442\u044c \u0435\u0441\u0442\u0435\u0441\u0442\u0432\u0435\u043d\u043d\u044b\u043c \u044f\u0437\u044b\u043a\u043e\u043c!"}, "icon": "\u2328\ufe0f"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What does the bot send every morning?", "id": "Apa yang dikirim bot setiap pagi?", "ru": "\u0427\u0442\u043e \u0431\u043e\u0442 \u043f\u0440\u0438\u0441\u044b\u043b\u0430\u0435\u0442 \u043a\u0430\u0436\u0434\u043e\u0435 \u0443\u0442\u0440\u043e?"}, "options": [
                {"value": "morning_briefing", "label": {"en": "Morning briefing with tasks and achievements", "id": "Briefing pagi dengan tugas dan pencapaian", "ru": "\u0423\u0442\u0440\u0435\u043d\u043d\u0438\u0439 \u0431\u0440\u0438\u0444\u0438\u043d\u0433 \u0441 \u0437\u0430\u0434\u0430\u0447\u0430\u043c\u0438 \u0438 \u0434\u043e\u0441\u0442\u0438\u0436\u0435\u043d\u0438\u044f\u043c\u0438"}},
                {"value": "joke", "label": {"en": "A joke", "id": "Lelucon", "ru": "\u0428\u0443\u0442\u043a\u0443"}},
                {"value": "nothing", "label": {"en": "Nothing", "id": "Tidak ada", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e"}},
            ]},
            {"id": "q2", "question": {"en": "What happens when you send a recipe photo?", "id": "Apa yang terjadi saat Anda mengirim foto resep?", "ru": "\u0427\u0442\u043e \u043f\u0440\u043e\u0438\u0441\u0445\u043e\u0434\u0438\u0442 \u043f\u0440\u0438 \u043e\u0442\u043f\u0440\u0430\u0432\u043a\u0435 \u0444\u043e\u0442\u043e \u0440\u0435\u0446\u0435\u043f\u0442\u0430?"}, "options": [
                {"value": "photo_ocr", "label": {"en": "OCR reads it, compares with spec, awards points", "id": "OCR membaca, membandingkan dengan spek, memberikan poin", "ru": "OCR \u0447\u0438\u0442\u0430\u0435\u0442, \u0441\u0440\u0430\u0432\u043d\u0438\u0432\u0430\u0435\u0442 \u0441\u043e \u0441\u043f\u0435\u043a\u043e\u0439, \u043d\u0430\u0447\u0438\u0441\u043b\u044f\u0435\u0442 \u043e\u0447\u043a\u0438"}},
                {"value": "nothing", "label": {"en": "Nothing special", "id": "Tidak ada yang spesial", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e \u043e\u0441\u043e\u0431\u0435\u043d\u043d\u043e\u0433\u043e"}},
                {"value": "error", "label": {"en": "It shows an error", "id": "Menampilkan error", "ru": "\u041f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442 \u043e\u0448\u0438\u0431\u043a\u0443"}},
            ]},
            {"id": "q3", "question": {"en": "How can you interact with the bot?", "id": "Bagaimana cara berinteraksi dengan bot?", "ru": "\u041a\u0430\u043a \u0432\u0437\u0430\u0438\u043c\u043e\u0434\u0435\u0439\u0441\u0442\u0432\u043e\u0432\u0430\u0442\u044c \u0441 \u0431\u043e\u0442\u043e\u043c?"}, "options": [
                {"value": "slash_commands", "label": {"en": "Slash commands and natural language", "id": "Perintah slash dan bahasa alami", "ru": "\u0421\u043b\u044d\u0448-\u043a\u043e\u043c\u0430\u043d\u0434\u044b \u0438 \u0435\u0441\u0442\u0435\u0441\u0442\u0432\u0435\u043d\u043d\u044b\u0439 \u044f\u0437\u044b\u043a"}},
                {"value": "only_buttons", "label": {"en": "Only buttons", "id": "Hanya tombol", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043a\u043d\u043e\u043f\u043a\u0438"}},
                {"value": "voice", "label": {"en": "Voice only", "id": "Hanya suara", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0433\u043e\u043b\u043e\u0441"}},
            ]},
        ],
    },
    "reports": {
        "icon": "\U0001f4ca",
        "title": {"en": "Reports & Analytics", "id": "Laporan & Analitik", "ru": "\u041e\u0442\u0447\u0451\u0442\u044b \u0438 \u0430\u043d\u0430\u043b\u0438\u0442\u0438\u043a\u0430"},
        "slides": [
            {"title": {"en": "Analytics Dashboard", "id": "Dashboard Analitik", "ru": "\u0414\u0430\u0448\u0431\u043e\u0440\u0434 \u0430\u043d\u0430\u043b\u0438\u0442\u0438\u043a\u0438"}, "content": {"en": "Real-time production analytics: kiln utilization, throughput, defect rates, material consumption, lead times. Visual charts help spot trends and bottlenecks.", "id": "Analitik produksi real-time: utilisasi kiln, throughput, tingkat cacat.", "ru": "\u0410\u043d\u0430\u043b\u0438\u0442\u0438\u043a\u0430 \u0432 \u0440\u0435\u0430\u043b\u044c\u043d\u043e\u043c \u0432\u0440\u0435\u043c\u0435\u043d\u0438: \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u043f\u0435\u0447\u0435\u0439, \u043f\u0440\u043e\u043f\u0443\u0441\u043a\u043d\u0430\u044f \u0441\u043f\u043e\u0441\u043e\u0431\u043d\u043e\u0441\u0442\u044c, \u0434\u0435\u0444\u0435\u043a\u0442\u044b, \u0440\u0430\u0441\u0445\u043e\u0434 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432."}, "icon": "\U0001f4c8"},
            {"title": {"en": "Export Options", "id": "Opsi Ekspor", "ru": "\u042d\u043a\u0441\u043f\u043e\u0440\u0442"}, "content": {"en": "Export reports as PDF or Excel. Generate CEO-level summaries with key KPIs. Share reports via Telegram or email.", "id": "Ekspor laporan sebagai PDF atau Excel. Buat ringkasan level CEO.", "ru": "\u042d\u043a\u0441\u043f\u043e\u0440\u0442 \u0432 PDF \u0438\u043b\u0438 Excel. CEO-\u0441\u0432\u043e\u0434\u043a\u0438 \u0441 \u043a\u043b\u044e\u0447\u0435\u0432\u044b\u043c\u0438 KPI."}, "icon": "\U0001f4e4"},
            {"title": {"en": "Lead Time Tracking", "id": "Pelacakan Lead Time", "ru": "\u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u0435 \u0441\u0440\u043e\u043a\u043e\u0432"}, "content": {"en": "Track average lead time per factory, collection, product type. See trends over time. Identify slow stages. Use data to improve production planning.", "id": "Lacak rata-rata lead time per pabrik, koleksi, jenis produk.", "ru": "\u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0439\u0442\u0435 \u0441\u0440\u0435\u0434\u043d\u0438\u0439 \u043b\u0438\u0434-\u0442\u0430\u0439\u043c \u043f\u043e \u0444\u0430\u0431\u0440\u0438\u043a\u0435, \u043a\u043e\u043b\u043b\u0435\u043a\u0446\u0438\u0438, \u0442\u0438\u043f\u0443 \u043f\u0440\u043e\u0434\u0443\u043a\u0442\u0430."}, "icon": "\u23f1\ufe0f"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "Where do you see production analytics?", "id": "Di mana Anda melihat analitik produksi?", "ru": "\u0413\u0434\u0435 \u0441\u043c\u043e\u0442\u0440\u0435\u0442\u044c \u0430\u043d\u0430\u043b\u0438\u0442\u0438\u043a\u0443?"}, "options": [
                {"value": "analytics_dashboard", "label": {"en": "Analytics Dashboard / Reports page", "id": "Dashboard Analitik / Halaman Laporan", "ru": "\u0414\u0430\u0448\u0431\u043e\u0440\u0434 \u0430\u043d\u0430\u043b\u0438\u0442\u0438\u043a\u0438 / \u041e\u0442\u0447\u0451\u0442\u044b"}},
                {"value": "email", "label": {"en": "Email reports", "id": "Laporan email", "ru": "Email \u043e\u0442\u0447\u0451\u0442\u044b"}},
                {"value": "nowhere", "label": {"en": "Not available", "id": "Tidak tersedia", "ru": "\u041d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e"}},
            ]},
            {"id": "q2", "question": {"en": "In what formats can you export reports?", "id": "Dalam format apa Anda bisa ekspor laporan?", "ru": "\u0412 \u043a\u0430\u043a\u0438\u0445 \u0444\u043e\u0440\u043c\u0430\u0442\u0430\u0445 \u044d\u043a\u0441\u043f\u043e\u0440\u0442?"}, "options": [
                {"value": "export_pdf_excel", "label": {"en": "PDF and Excel", "id": "PDF dan Excel", "ru": "PDF \u0438 Excel"}},
                {"value": "only_pdf", "label": {"en": "PDF only", "id": "Hanya PDF", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e PDF"}},
                {"value": "csv", "label": {"en": "CSV only", "id": "Hanya CSV", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e CSV"}},
            ]},
            {"id": "q3", "question": {"en": "What is a key metric to track?", "id": "Apa metrik kunci yang harus dilacak?", "ru": "\u041a\u0430\u043a\u043e\u0439 \u043a\u043b\u044e\u0447\u0435\u0432\u043e\u0439 \u043f\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u044c \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0442\u044c?"}, "options": [
                {"value": "lead_time", "label": {"en": "Lead time per factory and product", "id": "Lead time per pabrik dan produk", "ru": "\u041b\u0438\u0434-\u0442\u0430\u0439\u043c \u043f\u043e \u0444\u0430\u0431\u0440\u0438\u043a\u0435 \u0438 \u043f\u0440\u043e\u0434\u0443\u043a\u0442\u0443"}},
                {"value": "headcount", "label": {"en": "Employee headcount", "id": "Jumlah karyawan", "ru": "\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u0441\u043e\u0442\u0440\u0443\u0434\u043d\u0438\u043a\u043e\u0432"}},
                {"value": "weather", "label": {"en": "Weather forecast", "id": "Prakiraan cuaca", "ru": "\u041f\u0440\u043e\u0433\u043d\u043e\u0437 \u043f\u043e\u0433\u043e\u0434\u044b"}},
            ]},
        ],
    },
    "gamification": {
        "icon": "\U0001f3ae",
        "title": {"en": "Points & Gamification", "id": "Poin & Gamifikasi", "ru": "\u041e\u0447\u043a\u0438 \u0438 \u0433\u0435\u0439\u043c\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u044f"},
        "slides": [
            {"title": {"en": "Accuracy Scoring", "id": "Penilaian Akurasi", "ru": "\u041e\u0446\u0435\u043d\u043a\u0430 \u0442\u043e\u0447\u043d\u043e\u0441\u0442\u0438"}, "content": {"en": "Earn points for recipe accuracy: +/-1% = 10pts, +/-3% = 7pts, +/-5% = 5pts, +/-10% = 3pts, worse = 1pt. Photo verification bonus: +2 pts per verified photo.", "id": "Dapatkan poin untuk akurasi resep: +/-1% = 10pts, +/-3% = 7pts. Bonus verifikasi foto: +2 pts.", "ru": "\u041e\u0447\u043a\u0438 \u0437\u0430 \u0442\u043e\u0447\u043d\u043e\u0441\u0442\u044c \u0440\u0435\u0446\u0435\u043f\u0442\u0443\u0440\u044b: +/-1% = 10, +/-3% = 7, +/-5% = 5, +/-10% = 3. \u0411\u043e\u043d\u0443\u0441 \u0437\u0430 \u0444\u043e\u0442\u043e: +2."}, "icon": "\U0001f3af"},
            {"title": {"en": "Leaderboards & Achievements", "id": "Papan Peringkat & Pencapaian", "ru": "\u0420\u0435\u0439\u0442\u0438\u043d\u0433\u0438 \u0438 \u0434\u043e\u0441\u0442\u0438\u0436\u0435\u043d\u0438\u044f"}, "content": {"en": "Monthly leaderboards show top performers. Earn badges for milestones: first QC passed, 100 tiles verified, zero defects streak. Check /leaderboard in Telegram.", "id": "Papan peringkat bulanan menampilkan performa terbaik. Dapatkan badge untuk pencapaian.", "ru": "\u0415\u0436\u0435\u043c\u0435\u0441\u044f\u0447\u043d\u044b\u0435 \u0440\u0435\u0439\u0442\u0438\u043d\u0433\u0438, \u0431\u0435\u0439\u0434\u0436\u0438 \u0437\u0430 \u0434\u043e\u0441\u0442\u0438\u0436\u0435\u043d\u0438\u044f. \u041f\u0440\u043e\u0432\u0435\u0440\u044c /leaderboard \u0432 Telegram."}, "icon": "\U0001f3c6"},
            {"title": {"en": "Daily Challenges", "id": "Tantangan Harian", "ru": "\u0415\u0436\u0435\u0434\u043d\u0435\u0432\u043d\u044b\u0435 \u0432\u044b\u0437\u043e\u0432\u044b"}, "content": {"en": "Each day brings a new challenge: verify 5 recipes, achieve 95% accuracy, complete all tasks before noon. Bonus points for completing challenges. Check /challenge to see today's.", "id": "Setiap hari ada tantangan baru: verifikasi 5 resep, capai akurasi 95%, selesaikan tugas sebelum siang.", "ru": "\u041a\u0430\u0436\u0434\u044b\u0439 \u0434\u0435\u043d\u044c \u2014 \u043d\u043e\u0432\u044b\u0439 \u0432\u044b\u0437\u043e\u0432: \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c 5 \u0440\u0435\u0446\u0435\u043f\u0442\u043e\u0432, \u0434\u043e\u0441\u0442\u0438\u0447\u044c 95% \u0442\u043e\u0447\u043d\u043e\u0441\u0442\u0438. \u0411\u043e\u043d\u0443\u0441\u043d\u044b\u0435 \u043e\u0447\u043a\u0438!"}, "icon": "\U0001f4aa"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "How are accuracy points calculated?", "id": "Bagaimana poin akurasi dihitung?", "ru": "\u041a\u0430\u043a \u0441\u0447\u0438\u0442\u0430\u044e\u0442\u0441\u044f \u043e\u0447\u043a\u0438 \u0442\u043e\u0447\u043d\u043e\u0441\u0442\u0438?"}, "options": [
                {"value": "accuracy_scoring", "label": {"en": "Based on deviation percentage from recipe spec", "id": "Berdasarkan persentase penyimpangan dari spek resep", "ru": "\u041f\u043e \u043f\u0440\u043e\u0446\u0435\u043d\u0442\u0443 \u043e\u0442\u043a\u043b\u043e\u043d\u0435\u043d\u0438\u044f \u043e\u0442 \u0441\u043f\u0435\u043a\u0438"}},
                {"value": "flat", "label": {"en": "Flat 10 points per recipe", "id": "10 poin tetap per resep", "ru": "\u0424\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u043e 10 \u043e\u0447\u043a\u043e\u0432"}},
                {"value": "random", "label": {"en": "Random points", "id": "Poin acak", "ru": "\u0421\u043b\u0443\u0447\u0430\u0439\u043d\u044b\u0435 \u043e\u0447\u043a\u0438"}},
            ]},
            {"id": "q2", "question": {"en": "Where do you check the leaderboard?", "id": "Di mana Anda memeriksa papan peringkat?", "ru": "\u0413\u0434\u0435 \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0440\u0435\u0439\u0442\u0438\u043d\u0433?"}, "options": [
                {"value": "leaderboard", "label": {"en": "Telegram /leaderboard command or web dashboard", "id": "Perintah /leaderboard di Telegram atau dashboard web", "ru": "\u041a\u043e\u043c\u0430\u043d\u0434\u0430 /leaderboard \u0432 Telegram \u0438\u043b\u0438 \u0434\u0430\u0448\u0431\u043e\u0440\u0434"}},
                {"value": "email", "label": {"en": "Weekly email", "id": "Email mingguan", "ru": "\u0415\u0436\u0435\u043d\u0435\u0434\u0435\u043b\u044c\u043d\u044b\u0439 email"}},
                {"value": "nowhere", "label": {"en": "Not available", "id": "Tidak tersedia", "ru": "\u041d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e"}},
            ]},
            {"id": "q3", "question": {"en": "What are daily challenges?", "id": "Apa itu tantangan harian?", "ru": "\u0427\u0442\u043e \u0442\u0430\u043a\u043e\u0435 \u0435\u0436\u0435\u0434\u043d\u0435\u0432\u043d\u044b\u0435 \u0432\u044b\u0437\u043e\u0432\u044b?"}, "options": [
                {"value": "daily_challenges", "label": {"en": "Specific goals each day for bonus points", "id": "Tujuan spesifik setiap hari untuk poin bonus", "ru": "\u041a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u044b\u0435 \u0446\u0435\u043b\u0438 \u043d\u0430 \u0434\u0435\u043d\u044c \u0437\u0430 \u0431\u043e\u043d\u0443\u0441\u043d\u044b\u0435 \u043e\u0447\u043a\u0438"}},
                {"value": "puzzles", "label": {"en": "Puzzle games", "id": "Permainan puzzle", "ru": "\u041f\u0430\u0437\u043b\u044b"}},
                {"value": "nothing", "label": {"en": "Nothing, just a name", "id": "Tidak ada, hanya nama", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e, \u043f\u0440\u043e\u0441\u0442\u043e \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435"}},
            ]},
            {"id": "q4", "question": {"en": "When do points reset?", "id": "Kapan poin direset?", "ru": "\u041a\u043e\u0433\u0434\u0430 \u043e\u0447\u043a\u0438 \u0441\u0431\u0440\u0430\u0441\u044b\u0432\u0430\u044e\u0442\u0441\u044f?"}, "options": [
                {"value": "jan_reset", "label": {"en": "January 1st (yearly reset)", "id": "1 Januari (reset tahunan)", "ru": "1 \u044f\u043d\u0432\u0430\u0440\u044f (\u0435\u0436\u0435\u0433\u043e\u0434\u043d\u044b\u0439 \u0441\u0431\u0440\u043e\u0441)"}},
                {"value": "never", "label": {"en": "Never", "id": "Tidak pernah", "ru": "\u041d\u0438\u043a\u043e\u0433\u0434\u0430"}},
                {"value": "monthly", "label": {"en": "Monthly", "id": "Bulanan", "ru": "\u0415\u0436\u0435\u043c\u0435\u0441\u044f\u0447\u043d\u043e"}},
            ]},
        ],
    },
    "advanced": {
        "icon": "\U0001f9e0",
        "title": {"en": "Advanced Topics", "id": "Topik Lanjutan", "ru": "\u041f\u0440\u043e\u0434\u0432\u0438\u043d\u0443\u0442\u044b\u0435 \u0442\u0435\u043c\u044b"},
        "slides": [
            {"title": {"en": "Temperature Groups", "id": "Grup Suhu", "ru": "\u0422\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u043d\u044b\u0435 \u0433\u0440\u0443\u043f\u043f\u044b"}, "content": {"en": "Recipes are grouped by firing temperature. Compatible recipes can share a kiln batch. This maximizes kiln utilization and reduces energy costs.", "id": "Resep dikelompokkan berdasarkan suhu pembakaran. Resep kompatibel bisa berbagi batch kiln.", "ru": "\u0420\u0435\u0446\u0435\u043f\u0442\u044b \u0433\u0440\u0443\u043f\u043f\u0438\u0440\u0443\u044e\u0442\u0441\u044f \u043f\u043e \u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0435 \u043e\u0431\u0436\u0438\u0433\u0430. \u0421\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u044b\u0435 \u0440\u0435\u0446\u0435\u043f\u0442\u044b \u043c\u043e\u0433\u0443\u0442 \u0434\u0435\u043b\u0438\u0442\u044c \u043f\u0430\u0440\u0442\u0438\u044e."}, "icon": "\U0001f321\ufe0f"},
            {"title": {"en": "Zone-Based Capacity", "id": "Kapasitas Berbasis Zona", "ru": "\u0417\u043e\u043d\u043d\u0430\u044f \u0451\u043c\u043a\u043e\u0441\u0442\u044c"}, "content": {"en": "Kilns have edge and flat loading zones. Small tiles go flat, large tiles go on edge. The scheduler checks zone capacity independently, allowing 10% overflow per zone.", "id": "Kiln memiliki zona edge dan flat. Ubin kecil datar, ubin besar di tepi.", "ru": "\u041f\u0435\u0447\u0438 \u0438\u043c\u0435\u044e\u0442 \u0437\u043e\u043d\u044b: \u0440\u0435\u0431\u0440\u043e\u0432\u0430\u044f \u0438 \u043f\u043b\u043e\u0441\u043a\u0430\u044f. \u041c\u0430\u043b\u0435\u043d\u044c\u043a\u0438\u0435 \u043f\u043b\u0438\u0442\u043a\u0438 \u2014 \u043f\u043b\u043e\u0441\u043a\u043e, \u0431\u043e\u043b\u044c\u0448\u0438\u0435 \u2014 \u043d\u0430 \u0440\u0435\u0431\u0440\u043e."}, "icon": "\U0001f4d0"},
            {"title": {"en": "Defect Coefficient Matrix", "id": "Matriks Koefisien Cacat", "ru": "\u041c\u0430\u0442\u0440\u0438\u0446\u0430 \u043a\u043e\u044d\u0444\u0444\u0438\u0446\u0438\u0435\u043d\u0442\u043e\u0432 \u0434\u0435\u0444\u0435\u043a\u0442\u043e\u0432"}, "content": {"en": "Different glaze+product combinations have different expected defect rates. The 2D matrix (glaze type x product type) predicts how many extra tiles to produce. This replaces the old 1D size-only coefficient.", "id": "Kombinasi glasir+produk memiliki tingkat cacat yang berbeda.", "ru": "\u0420\u0430\u0437\u043d\u044b\u0435 \u043a\u043e\u043c\u0431\u0438\u043d\u0430\u0446\u0438\u0438 \u0433\u043b\u0430\u0437\u0443\u0440\u044c+\u043f\u0440\u043e\u0434\u0443\u043a\u0442 \u0438\u043c\u0435\u044e\u0442 \u0440\u0430\u0437\u043d\u044b\u0439 \u043f\u0440\u043e\u0446\u0435\u043d\u0442 \u0431\u0440\u0430\u043a\u0430. 2D-\u043c\u0430\u0442\u0440\u0438\u0446\u0430 \u043f\u0440\u0435\u0434\u0441\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442 \u043d\u0443\u0436\u043d\u044b\u0439 \u0437\u0430\u043f\u0430\u0441."}, "icon": "\U0001f4d0"},
            {"title": {"en": "Engobe & Shelf Coating", "id": "Engobe & Pelapisan Rak", "ru": "\u042d\u043d\u0433\u043e\u0431 \u0438 \u043f\u043e\u043a\u0440\u044b\u0442\u0438\u0435 \u043f\u043e\u043b\u043e\u043a"}, "content": {"en": "Engobe shelf coating recipes define material consumption per batch based on kiln area. The system auto-calculates consumption per firing. Different kiln types need different coating amounts.", "id": "Resep pelapisan rak engobe mendefinisikan konsumsi material per batch.", "ru": "\u0420\u0435\u0446\u0435\u043f\u0442\u044b \u043f\u043e\u043a\u0440\u044b\u0442\u0438\u044f \u043f\u043e\u043b\u043e\u043a \u044d\u043d\u0433\u043e\u0431\u043e\u043c \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u044f\u044e\u0442 \u0440\u0430\u0441\u0445\u043e\u0434 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u0430 \u043d\u0430 \u043f\u0430\u0440\u0442\u0438\u044e \u043f\u043e \u043f\u043b\u043e\u0449\u0430\u0434\u0438 \u043f\u0435\u0447\u0438."}, "icon": "\U0001f3a8"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "Why are recipes grouped by temperature?", "id": "Mengapa resep dikelompokkan berdasarkan suhu?", "ru": "\u0417\u0430\u0447\u0435\u043c \u0440\u0435\u0446\u0435\u043f\u0442\u044b \u0433\u0440\u0443\u043f\u043f\u0438\u0440\u0443\u044e\u0442\u0441\u044f \u043f\u043e \u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0435?"}, "options": [
                {"value": "temperature_groups", "label": {"en": "To combine compatible orders in the same kiln batch", "id": "Untuk menggabungkan pesanan kompatibel dalam batch kiln yang sama", "ru": "\u0427\u0442\u043e\u0431\u044b \u043e\u0431\u044a\u0435\u0434\u0438\u043d\u044f\u0442\u044c \u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u044b\u0435 \u0437\u0430\u043a\u0430\u0437\u044b \u0432 \u043e\u0434\u043d\u043e\u0439 \u043f\u0430\u0440\u0442\u0438\u0438"}},
                {"value": "decoration", "label": {"en": "For decorative purposes", "id": "Untuk tujuan dekoratif", "ru": "\u0414\u043b\u044f \u043a\u0440\u0430\u0441\u043e\u0442\u044b"}},
                {"value": "sorting", "label": {"en": "Just for sorting recipes", "id": "Hanya untuk mengurutkan resep", "ru": "\u0414\u043b\u044f \u0441\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u043a\u0438"}},
            ]},
            {"id": "q2", "question": {"en": "How does zone-based kiln capacity work?", "id": "Bagaimana kapasitas kiln berbasis zona bekerja?", "ru": "\u041a\u0430\u043a \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u0437\u043e\u043d\u043d\u0430\u044f \u0451\u043c\u043a\u043e\u0441\u0442\u044c?"}, "options": [
                {"value": "zone_capacity", "label": {"en": "Edge zone for large tiles, flat zone for small tiles", "id": "Zona tepi untuk ubin besar, zona datar untuk ubin kecil", "ru": "\u0420\u0435\u0431\u0440\u043e\u0432\u0430\u044f \u0437\u043e\u043d\u0430 \u0434\u043b\u044f \u043a\u0440\u0443\u043f\u043d\u044b\u0445, \u043f\u043b\u043e\u0441\u043a\u0430\u044f \u0434\u043b\u044f \u043c\u0435\u043b\u043a\u0438\u0445"}},
                {"value": "single", "label": {"en": "One zone for everything", "id": "Satu zona untuk semua", "ru": "\u041e\u0434\u043d\u0430 \u0437\u043e\u043d\u0430 \u0434\u043b\u044f \u0432\u0441\u0435\u0433\u043e"}},
                {"value": "random", "label": {"en": "Random placement", "id": "Penempatan acak", "ru": "\u0421\u043b\u0443\u0447\u0430\u0439\u043d\u043e\u0435 \u0440\u0430\u0437\u043c\u0435\u0449\u0435\u043d\u0438\u0435"}},
            ]},
            {"id": "q3", "question": {"en": "What replaced the 1D defect coefficient?", "id": "Apa yang menggantikan koefisien cacat 1D?", "ru": "\u0427\u0442\u043e \u0437\u0430\u043c\u0435\u043d\u0438\u043b\u043e 1D-\u043a\u043e\u044d\u0444\u0444\u0438\u0446\u0438\u0435\u043d\u0442 \u0431\u0440\u0430\u043a\u0430?"}, "options": [
                {"value": "defect_coefficient", "label": {"en": "2D matrix (glaze type x product type)", "id": "Matriks 2D (jenis glasir x jenis produk)", "ru": "2D-\u043c\u0430\u0442\u0440\u0438\u0446\u0430 (\u0433\u043b\u0430\u0437\u0443\u0440\u044c x \u043f\u0440\u043e\u0434\u0443\u043a\u0442)"}},
                {"value": "nothing", "label": {"en": "Nothing, it's still 1D", "id": "Tidak ada, masih 1D", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e, \u0432\u0441\u0451 \u0435\u0449\u0451 1D"}},
                {"value": "ai", "label": {"en": "AI prediction only", "id": "Hanya prediksi AI", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e AI-\u043f\u0440\u0435\u0434\u0438\u043a\u0446\u0438\u044f"}},
            ]},
            {"id": "q4", "question": {"en": "What determines engobe shelf coating consumption?", "id": "Apa yang menentukan konsumsi pelapisan rak engobe?", "ru": "\u0427\u0442\u043e \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u044f\u0435\u0442 \u0440\u0430\u0441\u0445\u043e\u0434 \u044d\u043d\u0433\u043e\u0431\u0430 \u043d\u0430 \u043f\u043e\u043b\u043a\u0438?"}, "options": [
                {"value": "engobe_shelf_coating", "label": {"en": "Kiln area and recipe spec", "id": "Area kiln dan spesifikasi resep", "ru": "\u041f\u043b\u043e\u0449\u0430\u0434\u044c \u043f\u0435\u0447\u0438 \u0438 \u0440\u0435\u0446\u0435\u043f\u0442\u0443\u0440\u0430"}},
                {"value": "fixed", "label": {"en": "Fixed amount per batch", "id": "Jumlah tetap per batch", "ru": "\u0424\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u043e\u0435 \u043a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e"}},
                {"value": "manual", "label": {"en": "Manual entry only", "id": "Hanya entri manual", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0432\u0440\u0443\u0447\u043d\u0443\u044e"}},
            ]},
        ],
    },
}
