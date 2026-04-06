"""Purchaser onboarding content."""

SECTIONS = ["purch_overview", "purch_requests", "purch_suppliers", "purch_stock_monitoring", "purch_costs"]

QUIZ_ANSWERS: dict[str, dict[str, str]] = {
    "purch_overview": {"q1": "materials_procurement", "q2": "purchase_requests", "q3": "prevent_production_stops"},
    "purch_requests": {"q1": "pm_creates", "q2": "five_statuses", "q3": "approve_then_order"},
    "purch_suppliers": {"q1": "compare_quotes", "q2": "quality_price_time", "q3": "supplier_database"},
    "purch_stock_monitoring": {"q1": "min_balance_alerts", "q2": "telegram_notification", "q3": "proactive_ordering"},
    "purch_costs": {"q1": "track_per_material", "q2": "cost_trends", "q3": "budget_optimization"},
}

ONBOARDING_CONTENT = {
    "purch_overview": {
        "icon": "\U0001f6d2",
        "title": {"en": "Purchaser Overview", "id": "Ikhtisar Purchaser", "ru": "\u041e\u0431\u0437\u043e\u0440 \u0437\u0430\u043a\u0443\u043f\u0449\u0438\u043a\u0430"},
        "slides": [
            {"title": {"en": "Your Role", "id": "Peran Anda", "ru": "\u0412\u0430\u0448\u0430 \u0440\u043e\u043b\u044c"}, "content": {"en": "As Purchaser, you ensure the factory never runs out of materials. You handle purchase requests, find suppliers, compare quotes, and track deliveries. Timely procurement prevents production stops.", "id": "Sebagai Purchaser, Anda memastikan pabrik tidak pernah kehabisan material. Anda menangani permintaan pembelian, mencari supplier, membandingkan penawaran.", "ru": "\u0412\u044b \u043e\u0431\u0435\u0441\u043f\u0435\u0447\u0438\u0432\u0430\u0435\u0442\u0435 \u0431\u0435\u0441\u043f\u0435\u0440\u0435\u0431\u043e\u0439\u043d\u043e\u0435 \u0441\u043d\u0430\u0431\u0436\u0435\u043d\u0438\u0435 \u0444\u0430\u0431\u0440\u0438\u043a\u0438. \u0417\u0430\u044f\u0432\u043a\u0438, \u043f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a\u0438, \u043a\u043e\u0442\u0438\u0440\u043e\u0432\u043a\u0438, \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u0435 \u0434\u043e\u0441\u0442\u0430\u0432\u043e\u043a."}, "icon": "\U0001f4e6"},
            {"title": {"en": "Request Flow", "id": "Alur Permintaan", "ru": "\u041f\u043e\u0442\u043e\u043a \u0437\u0430\u044f\u0432\u043e\u043a"}, "content": {"en": "Purchase requests flow: PM creates request -> You review -> Get quotes from suppliers -> Approve best option -> Order -> Track in-transit -> Receive at warehouse. Status: pending -> approved -> ordered -> in_transit -> received.", "id": "Alur permintaan pembelian: PM membuat -> Anda tinjau -> Dapatkan penawaran -> Setujui -> Pesan -> Lacak transit -> Terima di gudang.", "ru": "\u041f\u043e\u0442\u043e\u043a: PM \u0441\u043e\u0437\u0434\u0430\u0451\u0442 \u0437\u0430\u044f\u0432\u043a\u0443 -> \u0412\u044b \u043f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u0442\u0435 -> \u041a\u043e\u0442\u0438\u0440\u043e\u0432\u043a\u0438 -> \u041e\u0434\u043e\u0431\u0440\u0435\u043d\u0438\u0435 -> \u0417\u0430\u043a\u0430\u0437 -> \u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u0435 -> \u041f\u0440\u0438\u0451\u043c\u043a\u0430."}, "icon": "\U0001f504"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What is your main responsibility?", "id": "Apa tanggung jawab utama Anda?", "ru": "\u0412\u0430\u0448\u0430 \u0433\u043b\u0430\u0432\u043d\u0430\u044f \u0437\u0430\u0434\u0430\u0447\u0430?"}, "options": [
                {"value": "materials_procurement", "label": {"en": "Procuring materials so production never stops", "id": "Pengadaan material agar produksi tidak berhenti", "ru": "\u0417\u0430\u043a\u0443\u043f\u043a\u0430 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432 \u0434\u043b\u044f \u0431\u0435\u0441\u043f\u0435\u0440\u0435\u0431\u043e\u0439\u043d\u043e\u0439 \u0440\u0430\u0431\u043e\u0442\u044b"}},
                {"value": "sales", "label": {"en": "Selling products", "id": "Menjual produk", "ru": "\u041f\u0440\u043e\u0434\u0430\u0436\u0438"}},
                {"value": "hiring", "label": {"en": "Hiring employees", "id": "Merekrut karyawan", "ru": "\u041d\u0430\u0439\u043c \u0441\u043e\u0442\u0440\u0443\u0434\u043d\u0438\u043a\u043e\u0432"}},
            ]},
            {"id": "q2", "question": {"en": "How do you learn about material needs?", "id": "Bagaimana Anda mengetahui kebutuhan material?", "ru": "\u041a\u0430\u043a \u0443\u0437\u043d\u0430\u0451\u0442\u0435 \u043e \u043f\u043e\u0442\u0440\u0435\u0431\u043d\u043e\u0441\u0442\u0438?"}, "options": [
                {"value": "purchase_requests", "label": {"en": "Purchase requests from PM + stock alerts", "id": "Permintaan pembelian dari PM + peringatan stok", "ru": "\u0417\u0430\u044f\u0432\u043a\u0438 \u043e\u0442 PM + \u0430\u043b\u0435\u0440\u0442\u044b \u0441\u0442\u043e\u043a\u0430"}},
                {"value": "guessing", "label": {"en": "Guessing", "id": "Menebak", "ru": "\u0423\u0433\u0430\u0434\u044b\u0432\u0430\u043d\u0438\u0435"}},
                {"value": "daily_check", "label": {"en": "Daily warehouse walk", "id": "Jalan-jalan gudang harian", "ru": "\u0415\u0436\u0435\u0434\u043d\u0435\u0432\u043d\u044b\u0439 \u043e\u0431\u0445\u043e\u0434 \u0441\u043a\u043b\u0430\u0434\u0430"}},
            ]},
            {"id": "q3", "question": {"en": "Why is timely procurement critical?", "id": "Mengapa pengadaan tepat waktu penting?", "ru": "\u041f\u043e\u0447\u0435\u043c\u0443 \u0441\u0432\u043e\u0435\u0432\u0440\u0435\u043c\u0435\u043d\u043d\u0430\u044f \u0437\u0430\u043a\u0443\u043f\u043a\u0430 \u043a\u0440\u0438\u0442\u0438\u0447\u043d\u0430?"}, "options": [
                {"value": "prevent_production_stops", "label": {"en": "Prevents production stops", "id": "Mencegah berhentinya produksi", "ru": "\u041f\u0440\u0435\u0434\u043e\u0442\u0432\u0440\u0430\u0449\u0430\u0435\u0442 \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0443 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u0430"}},
                {"value": "not_important", "label": {"en": "Not that important", "id": "Tidak terlalu penting", "ru": "\u041d\u0435 \u0442\u0430\u043a \u0432\u0430\u0436\u043d\u043e"}},
                {"value": "cost_only", "label": {"en": "Only for cost savings", "id": "Hanya untuk penghematan biaya", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0434\u043b\u044f \u044d\u043a\u043e\u043d\u043e\u043c\u0438\u0438"}},
            ]},
        ],
    },
    "purch_requests": {
        "icon": "\U0001f4cb",
        "title": {"en": "Purchase Requests", "id": "Permintaan Pembelian", "ru": "\u0417\u0430\u044f\u0432\u043a\u0438 \u043d\u0430 \u0437\u0430\u043a\u0443\u043f\u043a\u0443"},
        "slides": [
            {"title": {"en": "Request Lifecycle", "id": "Siklus Permintaan", "ru": "\u0416\u0438\u0437\u043d\u0435\u043d\u043d\u044b\u0439 \u0446\u0438\u043a\u043b \u0437\u0430\u044f\u0432\u043a\u0438"}, "content": {"en": "Statuses: pending (new request) -> approved (you approve) -> ordered (placed with supplier) -> in_transit (shipping) -> received (arrived at warehouse). Update status at each step.", "id": "Status: pending -> approved -> ordered -> in_transit -> received. Perbarui status di setiap langkah.", "ru": "\u0421\u0442\u0430\u0442\u0443\u0441\u044b: pending -> approved -> ordered -> in_transit -> received. \u041e\u0431\u043d\u043e\u0432\u043b\u044f\u0439\u0442\u0435 \u043d\u0430 \u043a\u0430\u0436\u0434\u043e\u043c \u044d\u0442\u0430\u043f\u0435."}, "icon": "\U0001f504"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "Who creates purchase requests?", "id": "Siapa yang membuat permintaan pembelian?", "ru": "\u041a\u0442\u043e \u0441\u043e\u0437\u0434\u0430\u0451\u0442 \u0437\u0430\u044f\u0432\u043a\u0438?"}, "options": [
                {"value": "pm_creates", "label": {"en": "Production Manager", "id": "Manajer Produksi", "ru": "Production Manager"}},
                {"value": "auto", "label": {"en": "Automatic", "id": "Otomatis", "ru": "\u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438"}},
                {"value": "ceo", "label": {"en": "CEO", "id": "CEO", "ru": "CEO"}},
            ]},
            {"id": "q2", "question": {"en": "How many statuses does a request have?", "id": "Berapa status yang dimiliki permintaan?", "ru": "\u0421\u043a\u043e\u043b\u044c\u043a\u043e \u0441\u0442\u0430\u0442\u0443\u0441\u043e\u0432 \u0443 \u0437\u0430\u044f\u0432\u043a\u0438?"}, "options": [
                {"value": "five_statuses", "label": {"en": "5: pending, approved, ordered, in_transit, received", "id": "5: pending, approved, ordered, in_transit, received", "ru": "5: pending, approved, ordered, in_transit, received"}},
                {"value": "two", "label": {"en": "2: open and closed", "id": "2: terbuka dan tertutup", "ru": "2: \u043e\u0442\u043a\u0440\u044b\u0442\u0430 \u0438 \u0437\u0430\u043a\u0440\u044b\u0442\u0430"}},
                {"value": "three", "label": {"en": "3", "id": "3", "ru": "3"}},
            ]},
            {"id": "q3", "question": {"en": "What's the first action on a new request?", "id": "Aksi pertama pada permintaan baru?", "ru": "\u041f\u0435\u0440\u0432\u043e\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435 \u0441 \u043d\u043e\u0432\u043e\u0439 \u0437\u0430\u044f\u0432\u043a\u043e\u0439?"}, "options": [
                {"value": "approve_then_order", "label": {"en": "Review, approve, then find supplier and order", "id": "Tinjau, setujui, lalu cari supplier dan pesan", "ru": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c, \u043e\u0434\u043e\u0431\u0440\u0438\u0442\u044c, \u043d\u0430\u0439\u0442\u0438 \u043f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a\u0430"}},
                {"value": "ignore", "label": {"en": "Ignore it", "id": "Abaikan", "ru": "\u041f\u0440\u043e\u0438\u0433\u043d\u043e\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c"}},
                {"value": "forward", "label": {"en": "Forward to CEO", "id": "Teruskan ke CEO", "ru": "\u041f\u0435\u0440\u0435\u0441\u043b\u0430\u0442\u044c CEO"}},
            ]},
        ],
    },
    "purch_suppliers": {
        "icon": "\U0001f91d",
        "title": {"en": "Supplier Management", "id": "Manajemen Supplier", "ru": "\u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u043f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a\u0430\u043c\u0438"},
        "slides": [
            {"title": {"en": "Finding Suppliers", "id": "Mencari Supplier", "ru": "\u041f\u043e\u0438\u0441\u043a \u043f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a\u043e\u0432"}, "content": {"en": "Compare multiple suppliers for each material. Consider: price, delivery time, quality track record, minimum order quantity. Keep a supplier database in the system.", "id": "Bandingkan beberapa supplier untuk setiap material. Pertimbangkan: harga, waktu pengiriman, rekam jejak kualitas.", "ru": "\u0421\u0440\u0430\u0432\u043d\u0438\u0432\u0430\u0439\u0442\u0435 \u043f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a\u043e\u0432: \u0446\u0435\u043d\u0430, \u0441\u0440\u043e\u043a\u0438, \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u043e, \u043c\u0438\u043d. \u043f\u0430\u0440\u0442\u0438\u044f. \u0412\u0435\u0434\u0438\u0442\u0435 \u0431\u0430\u0437\u0443 \u043f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a\u043e\u0432."}, "icon": "\U0001f50d"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "How to choose a supplier?", "id": "Bagaimana memilih supplier?", "ru": "\u041a\u0430\u043a \u0432\u044b\u0431\u0440\u0430\u0442\u044c \u043f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a\u0430?"}, "options": [
                {"value": "compare_quotes", "label": {"en": "Compare quotes from multiple suppliers", "id": "Bandingkan penawaran dari beberapa supplier", "ru": "\u0421\u0440\u0430\u0432\u043d\u0438\u0442\u044c \u043a\u043e\u0442\u0438\u0440\u043e\u0432\u043a\u0438 \u043e\u0442 \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u0438\u0445"}},
                {"value": "cheapest", "label": {"en": "Always cheapest", "id": "Selalu termurah", "ru": "\u0412\u0441\u0435\u0433\u0434\u0430 \u0441\u0430\u043c\u044b\u0439 \u0434\u0435\u0448\u0451\u0432\u044b\u0439"}},
                {"value": "first", "label": {"en": "First available", "id": "Pertama yang tersedia", "ru": "\u041f\u0435\u0440\u0432\u044b\u0439 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0439"}},
            ]},
            {"id": "q2", "question": {"en": "What factors matter for supplier selection?", "id": "Faktor apa yang penting untuk pemilihan supplier?", "ru": "\u041a\u0430\u043a\u0438\u0435 \u0444\u0430\u043a\u0442\u043e\u0440\u044b \u0432\u0430\u0436\u043d\u044b?"}, "options": [
                {"value": "quality_price_time", "label": {"en": "Quality, price, delivery time", "id": "Kualitas, harga, waktu pengiriman", "ru": "\u041a\u0430\u0447\u0435\u0441\u0442\u0432\u043e, \u0446\u0435\u043d\u0430, \u0441\u0440\u043e\u043a\u0438"}},
                {"value": "price_only", "label": {"en": "Price only", "id": "Hanya harga", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0446\u0435\u043d\u0430"}},
                {"value": "distance", "label": {"en": "Distance only", "id": "Hanya jarak", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0440\u0430\u0441\u0441\u0442\u043e\u044f\u043d\u0438\u0435"}},
            ]},
            {"id": "q3", "question": {"en": "Where to track supplier info?", "id": "Di mana melacak info supplier?", "ru": "\u0413\u0434\u0435 \u0432\u0435\u0441\u0442\u0438 \u0431\u0430\u0437\u0443 \u043f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a\u043e\u0432?"}, "options": [
                {"value": "supplier_database", "label": {"en": "In the PMS supplier database", "id": "Di database supplier PMS", "ru": "\u0412 \u0431\u0430\u0437\u0435 \u043f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a\u043e\u0432 PMS"}},
                {"value": "paper", "label": {"en": "Paper notebook", "id": "Buku catatan kertas", "ru": "\u0411\u0443\u043c\u0430\u0436\u043d\u044b\u0439 \u0431\u043b\u043e\u043a\u043d\u043e\u0442"}},
                {"value": "memory", "label": {"en": "From memory", "id": "Dari ingatan", "ru": "\u041f\u043e \u043f\u0430\u043c\u044f\u0442\u0438"}},
            ]},
        ],
    },
    "purch_stock_monitoring": {
        "icon": "\U0001f4ca",
        "title": {"en": "Stock Monitoring", "id": "Pemantauan Stok", "ru": "\u041c\u043e\u043d\u0438\u0442\u043e\u0440\u0438\u043d\u0433 \u0441\u0442\u043e\u043a\u0430"},
        "slides": [
            {"title": {"en": "Proactive Monitoring", "id": "Pemantauan Proaktif", "ru": "\u041f\u0440\u043e\u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0439 \u043c\u043e\u043d\u0438\u0442\u043e\u0440\u0438\u043d\u0433"}, "content": {"en": "Don't wait for stockouts. Monitor material levels regularly. The system sends Telegram alerts when materials drop below minimum balance. Plan orders ahead of busy production periods.", "id": "Jangan tunggu kehabisan stok. Pantau level material secara rutin. Sistem mengirim peringatan Telegram.", "ru": "\u041d\u0435 \u0436\u0434\u0438\u0442\u0435 \u0434\u0435\u0444\u0438\u0446\u0438\u0442\u0430. \u0421\u043b\u0435\u0434\u0438\u0442\u0435 \u0437\u0430 \u0443\u0440\u043e\u0432\u043d\u044f\u043c\u0438. Telegram-\u0430\u043b\u0435\u0440\u0442\u044b \u043f\u0440\u0438 \u043f\u0430\u0434\u0435\u043d\u0438\u0438 \u043d\u0438\u0436\u0435 \u043c\u0438\u043d\u0438\u043c\u0443\u043c\u0430."}, "icon": "\U0001f514"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What alerts you to low stock?", "id": "Apa yang memperingatkan Anda tentang stok rendah?", "ru": "\u0427\u0442\u043e \u0441\u0438\u0433\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0435\u0442 \u043e \u043d\u0438\u0437\u043a\u043e\u043c \u0441\u0442\u043e\u043a\u0435?"}, "options": [
                {"value": "min_balance_alerts", "label": {"en": "Minimum balance alerts in the system", "id": "Peringatan saldo minimum di sistem", "ru": "\u0410\u043b\u0435\u0440\u0442\u044b \u043c\u0438\u043d\u0438\u043c\u0430\u043b\u044c\u043d\u043e\u0433\u043e \u0431\u0430\u043b\u0430\u043d\u0441\u0430"}},
                {"value": "guessing", "label": {"en": "Guessing", "id": "Menebak", "ru": "\u0423\u0433\u0430\u0434\u044b\u0432\u0430\u043d\u0438\u0435"}},
                {"value": "warehouse", "label": {"en": "Warehouse calls you", "id": "Gudang menelepon Anda", "ru": "\u0421\u043a\u043b\u0430\u0434 \u0437\u0432\u043e\u043d\u0438\u0442"}},
            ]},
            {"id": "q2", "question": {"en": "How are alerts delivered?", "id": "Bagaimana peringatan dikirim?", "ru": "\u041a\u0430\u043a \u043f\u0440\u0438\u0445\u043e\u0434\u044f\u0442 \u0430\u043b\u0435\u0440\u0442\u044b?"}, "options": [
                {"value": "telegram_notification", "label": {"en": "Telegram notification", "id": "Notifikasi Telegram", "ru": "\u0423\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0435 \u0432 Telegram"}},
                {"value": "email", "label": {"en": "Email only", "id": "Hanya email", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e email"}},
                {"value": "sms", "label": {"en": "SMS", "id": "SMS", "ru": "SMS"}},
            ]},
            {"id": "q3", "question": {"en": "Best practice for material ordering?", "id": "Praktik terbaik untuk pemesanan material?", "ru": "\u041b\u0443\u0447\u0448\u0430\u044f \u043f\u0440\u0430\u043a\u0442\u0438\u043a\u0430 \u0437\u0430\u043a\u0443\u043f\u043e\u043a?"}, "options": [
                {"value": "proactive_ordering", "label": {"en": "Order proactively before stock runs out", "id": "Pesan proaktif sebelum stok habis", "ru": "\u0417\u0430\u043a\u0430\u0437\u044b\u0432\u0430\u0442\u044c \u043f\u0440\u043e\u0430\u043a\u0442\u0438\u0432\u043d\u043e \u0434\u043e \u0434\u0435\u0444\u0438\u0446\u0438\u0442\u0430"}},
                {"value": "wait", "label": {"en": "Wait until completely out", "id": "Tunggu sampai habis", "ru": "\u0416\u0434\u0430\u0442\u044c \u043f\u043e\u043b\u043d\u043e\u0433\u043e \u0438\u0441\u0447\u0435\u0440\u043f\u0430\u043d\u0438\u044f"}},
                {"value": "bulk", "label": {"en": "Buy everything once a year", "id": "Beli semuanya setahun sekali", "ru": "\u041a\u0443\u043f\u0438\u0442\u044c \u0432\u0441\u0451 \u0440\u0430\u0437 \u0432 \u0433\u043e\u0434"}},
            ]},
        ],
    },
    "purch_costs": {
        "icon": "\U0001f4b0",
        "title": {"en": "Cost Management", "id": "Manajemen Biaya", "ru": "\u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0437\u0430\u0442\u0440\u0430\u0442\u0430\u043c\u0438"},
        "slides": [
            {"title": {"en": "Tracking Costs", "id": "Pelacakan Biaya", "ru": "\u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u0435 \u0437\u0430\u0442\u0440\u0430\u0442"}, "content": {"en": "Track cost per material over time. Spot price increases early. Negotiate bulk discounts. Report cost trends to CEO for budget planning.", "id": "Lacak biaya per material seiring waktu. Deteksi kenaikan harga lebih awal. Negosiasikan diskon grosir.", "ru": "\u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0439\u0442\u0435 \u0441\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u043e\u0432. \u0417\u0430\u043c\u0435\u0447\u0430\u0439\u0442\u0435 \u0440\u043e\u0441\u0442 \u0446\u0435\u043d. \u0414\u043e\u0433\u043e\u0432\u0430\u0440\u0438\u0432\u0430\u0439\u0442\u0435\u0441\u044c \u043e \u0441\u043a\u0438\u0434\u043a\u0430\u0445. \u041e\u0442\u0447\u0451\u0442\u044b CEO."}, "icon": "\U0001f4c8"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "How to track material costs?", "id": "Bagaimana melacak biaya material?", "ru": "\u041a\u0430\u043a \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0442\u044c \u0437\u0430\u0442\u0440\u0430\u0442\u044b?"}, "options": [
                {"value": "track_per_material", "label": {"en": "Per material cost tracking over time", "id": "Pelacakan biaya per material seiring waktu", "ru": "\u041f\u043e\u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044c\u043d\u043e\u0435 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u0435"}},
                {"value": "total_only", "label": {"en": "Total spend only", "id": "Hanya total pengeluaran", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043e\u0431\u0449\u0430\u044f \u0441\u0443\u043c\u043c\u0430"}},
                {"value": "not_tracked", "label": {"en": "Not tracked", "id": "Tidak dilacak", "ru": "\u041d\u0435 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0435\u0442\u0441\u044f"}},
            ]},
            {"id": "q2", "question": {"en": "What to report to CEO?", "id": "Apa yang dilaporkan ke CEO?", "ru": "\u0427\u0442\u043e \u0441\u043e\u043e\u0431\u0449\u0430\u0442\u044c CEO?"}, "options": [
                {"value": "cost_trends", "label": {"en": "Cost trends and price changes", "id": "Tren biaya dan perubahan harga", "ru": "\u0422\u0440\u0435\u043d\u0434\u044b \u0437\u0430\u0442\u0440\u0430\u0442 \u0438 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0446\u0435\u043d"}},
                {"value": "nothing", "label": {"en": "Nothing", "id": "Tidak ada", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e"}},
                {"value": "orders_only", "label": {"en": "Just order count", "id": "Hanya jumlah pesanan", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043a\u043e\u043b-\u0432\u043e \u0437\u0430\u043a\u0430\u0437\u043e\u0432"}},
            ]},
            {"id": "q3", "question": {"en": "How to reduce costs?", "id": "Bagaimana mengurangi biaya?", "ru": "\u041a\u0430\u043a \u0441\u043d\u0438\u0437\u0438\u0442\u044c \u0437\u0430\u0442\u0440\u0430\u0442\u044b?"}, "options": [
                {"value": "budget_optimization", "label": {"en": "Bulk discounts, early detection of price increases", "id": "Diskon grosir, deteksi dini kenaikan harga", "ru": "\u041e\u043f\u0442\u043e\u0432\u044b\u0435 \u0441\u043a\u0438\u0434\u043a\u0438, \u0440\u0430\u043d\u043d\u0435\u0435 \u043e\u0431\u043d\u0430\u0440\u0443\u0436\u0435\u043d\u0438\u0435 \u0440\u043e\u0441\u0442\u0430 \u0446\u0435\u043d"}},
                {"value": "cheapest", "label": {"en": "Always buy cheapest", "id": "Selalu beli termurah", "ru": "\u0412\u0441\u0435\u0433\u0434\u0430 \u0441\u0430\u043c\u043e\u0435 \u0434\u0435\u0448\u0451\u0432\u043e\u0435"}},
                {"value": "nothing", "label": {"en": "Can't reduce costs", "id": "Tidak bisa mengurangi biaya", "ru": "\u041d\u0435\u043b\u044c\u0437\u044f \u0441\u043d\u0438\u0437\u0438\u0442\u044c"}},
            ]},
        ],
    },
}
