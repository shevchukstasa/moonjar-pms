"""Sorter/Packer onboarding content."""

SECTIONS = ["sp_overview", "sp_grading", "sp_packing", "sp_photos", "sp_completion"]

QUIZ_ANSWERS: dict[str, dict[str, str]] = {
    "sp_overview": {"q1": "sort_and_pack", "q2": "after_final_qc", "q3": "grade_abc"},
    "sp_grading": {"q1": "visual_dimensions", "q2": "a_b_c", "q3": "qm_decision"},
    "sp_packing": {"q1": "by_order_grade", "q2": "prevent_damage", "q3": "label_each_box"},
    "sp_photos": {"q1": "documentation_proof", "q2": "telegram_bot", "q3": "points_earned"},
    "sp_completion": {"q1": "system_update", "q2": "warehouse_notification", "q3": "ready_for_shipment"},
}

ONBOARDING_CONTENT = {
    "sp_overview": {
        "icon": "\U0001f4e6",
        "title": {"en": "Sorter/Packer Overview", "id": "Ikhtisar Sortir/Packer", "ru": "\u041e\u0431\u0437\u043e\u0440 \u0441\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0449\u0438\u043a\u0430/\u0443\u043f\u0430\u043a\u043e\u0432\u0449\u0438\u043a\u0430"},
        "slides": [
            {"title": {"en": "Your Role", "id": "Peran Anda", "ru": "\u0412\u0430\u0448\u0430 \u0440\u043e\u043b\u044c"}, "content": {"en": "You sort tiles by grade after Final QC and pack them for shipment. Quality of packing directly affects customer satisfaction. Handle tiles carefully - they are handcrafted lava stone.", "id": "Anda mengurutkan ubin berdasarkan grade setelah Final QC dan mengemasnya untuk pengiriman. Kualitas pengemasan langsung memengaruhi kepuasan pelanggan.", "ru": "\u0412\u044b \u0441\u043e\u0440\u0442\u0438\u0440\u0443\u0435\u0442\u0435 \u043f\u043b\u0438\u0442\u043a\u0443 \u043f\u043e \u0433\u0440\u0435\u0439\u0434\u0430\u043c \u043f\u043e\u0441\u043b\u0435 QC \u0438 \u0443\u043f\u0430\u043a\u043e\u0432\u044b\u0432\u0430\u0435\u0442\u0435. \u041a\u0430\u0447\u0435\u0441\u0442\u0432\u043e \u0443\u043f\u0430\u043a\u043e\u0432\u043a\u0438 \u0432\u043b\u0438\u044f\u0435\u0442 \u043d\u0430 \u0443\u0434\u043e\u0432\u043b\u0435\u0442\u0432\u043e\u0440\u0451\u043d\u043d\u043e\u0441\u0442\u044c \u043a\u043b\u0438\u0435\u043d\u0442\u0430."}, "icon": "\U0001f3af"},
            {"title": {"en": "Grading System", "id": "Sistem Grading", "ru": "\u0421\u0438\u0441\u0442\u0435\u043c\u0430 \u0433\u0440\u0435\u0439\u0434\u043e\u0432"}, "content": {"en": "Tiles are sorted into grades: A (perfect), B (minor imperfections acceptable for most uses), C (visible imperfections, economy grade). Grade determines pricing and customer allocation.", "id": "Ubin diurutkan menjadi grade: A (sempurna), B (ketidaksempurnaan kecil), C (ketidaksempurnaan terlihat). Grade menentukan harga.", "ru": "\u0413\u0440\u0435\u0439\u0434\u044b: A (\u0438\u0434\u0435\u0430\u043b), B (\u043c\u0438\u043d\u043e\u0440\u043d\u044b\u0435 \u0434\u0435\u0444\u0435\u043a\u0442\u044b), C (\u0437\u0430\u043c\u0435\u0442\u043d\u044b\u0435 \u0434\u0435\u0444\u0435\u043a\u0442\u044b, \u044d\u043a\u043e\u043d\u043e\u043c). \u0413\u0440\u0435\u0439\u0434 \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u044f\u0435\u0442 \u0446\u0435\u043d\u0443."}, "icon": "\U0001f31f"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What is your main task?", "id": "Apa tugas utama Anda?", "ru": "\u0412\u0430\u0448\u0430 \u0433\u043b\u0430\u0432\u043d\u0430\u044f \u0437\u0430\u0434\u0430\u0447\u0430?"}, "options": [
                {"value": "sort_and_pack", "label": {"en": "Sort tiles by grade and pack for shipment", "id": "Sortir ubin berdasarkan grade dan kemas untuk pengiriman", "ru": "\u0421\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0438 \u0443\u043f\u0430\u043a\u043e\u0432\u044b\u0432\u0430\u0442\u044c"}},
                {"value": "firing", "label": {"en": "Fire tiles in kiln", "id": "Membakar ubin di kiln", "ru": "\u041e\u0431\u0436\u0438\u0433\u0430\u0442\u044c \u043f\u043b\u0438\u0442\u043a\u0443"}},
                {"value": "glazing", "label": {"en": "Apply glaze", "id": "Mengaplikasikan glasir", "ru": "\u041d\u0430\u043d\u043e\u0441\u0438\u0442\u044c \u0433\u043b\u0430\u0437\u0443\u0440\u044c"}},
            ]},
            {"id": "q2", "question": {"en": "When do you start sorting?", "id": "Kapan Anda mulai menyortir?", "ru": "\u041a\u043e\u0433\u0434\u0430 \u043d\u0430\u0447\u0438\u043d\u0430\u0435\u0442\u0435 \u0441\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u043a\u0443?"}, "options": [
                {"value": "after_final_qc", "label": {"en": "After tiles pass Final QC", "id": "Setelah ubin lolos Final QC", "ru": "\u041f\u043e\u0441\u043b\u0435 Final QC"}},
                {"value": "after_glazing", "label": {"en": "After glazing", "id": "Setelah glasir", "ru": "\u041f\u043e\u0441\u043b\u0435 \u0433\u043b\u0430\u0437\u0443\u0440\u043e\u0432\u043a\u0438"}},
                {"value": "anytime", "label": {"en": "Anytime", "id": "Kapan saja", "ru": "\u041a\u043e\u0433\u0434\u0430 \u0443\u0433\u043e\u0434\u043d\u043e"}},
            ]},
            {"id": "q3", "question": {"en": "What are the tile grades?", "id": "Apa grade ubin?", "ru": "\u041a\u0430\u043a\u0438\u0435 \u0433\u0440\u0435\u0439\u0434\u044b?"}, "options": [
                {"value": "grade_abc", "label": {"en": "A (perfect), B (minor), C (economy)", "id": "A (sempurna), B (kecil), C (ekonomi)", "ru": "A (\u0438\u0434\u0435\u0430\u043b), B (\u043c\u0438\u043d\u043e\u0440), C (\u044d\u043a\u043e\u043d\u043e\u043c)"}},
                {"value": "one_grade", "label": {"en": "One grade for all", "id": "Satu grade untuk semua", "ru": "\u041e\u0434\u0438\u043d \u0433\u0440\u0435\u0439\u0434 \u0434\u043b\u044f \u0432\u0441\u0435\u0445"}},
                {"value": "numbers", "label": {"en": "1-10 scale", "id": "Skala 1-10", "ru": "\u0428\u043a\u0430\u043b\u0430 1-10"}},
            ]},
        ],
    },
    "sp_grading": {
        "icon": "\U0001f31f",
        "title": {"en": "Tile Grading", "id": "Grading Ubin", "ru": "\u0413\u0440\u0435\u0439\u0434\u0438\u043d\u0433 \u043f\u043b\u0438\u0442\u043a\u0438"},
        "slides": [
            {"title": {"en": "How to Grade", "id": "Cara Grading", "ru": "\u041a\u0430\u043a \u0433\u0440\u0435\u0439\u0434\u0438\u0440\u043e\u0432\u0430\u0442\u044c"}, "content": {"en": "Check each tile visually: surface quality, color consistency, edge straightness, correct dimensions. Grade A: no visible defects. Grade B: minor imperfections. Grade C: noticeable but functional.", "id": "Periksa setiap ubin secara visual: kualitas permukaan, konsistensi warna, ketepatan tepi, dimensi.", "ru": "\u0412\u0438\u0437\u0443\u0430\u043b\u044c\u043d\u043e: \u043f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u044c, \u0446\u0432\u0435\u0442, \u043a\u0440\u0430\u044f, \u0440\u0430\u0437\u043c\u0435\u0440\u044b. A: \u0431\u0435\u0437 \u0434\u0435\u0444\u0435\u043a\u0442\u043e\u0432. B: \u043c\u0438\u043d\u043e\u0440\u043d\u044b\u0435. C: \u0437\u0430\u043c\u0435\u0442\u043d\u044b\u0435, \u043d\u043e \u0444\u0443\u043d\u043a\u0446\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u044b\u0435."}, "icon": "\U0001f50d"},
            {"title": {"en": "Borderline Cases", "id": "Kasus Batas", "ru": "\u041f\u043e\u0433\u0440\u0430\u043d\u0438\u0447\u043d\u044b\u0435 \u0441\u043b\u0443\u0447\u0430\u0438"}, "content": {"en": "When unsure about a grade, consult the Quality Manager. Some collections have specific grading criteria. Always err on the side of caution - it's better to downgrade than ship defective tiles.", "id": "Jika ragu tentang grade, konsultasikan dengan Manajer Kualitas. Lebih baik menurunkan grade daripada mengirim ubin cacat.", "ru": "\u041f\u0440\u0438 \u0441\u043e\u043c\u043d\u0435\u043d\u0438\u044f\u0445 \u2014 \u043a\u043e\u043d\u0441\u0443\u043b\u044c\u0442\u0438\u0440\u0443\u0439\u0442\u0435\u0441\u044c \u0441 QM. \u041b\u0443\u0447\u0448\u0435 \u043f\u043e\u043d\u0438\u0437\u0438\u0442\u044c \u0433\u0440\u0435\u0439\u0434, \u0447\u0435\u043c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0431\u0440\u0430\u043a."}, "icon": "\u2753"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What do you check when grading?", "id": "Apa yang Anda periksa saat grading?", "ru": "\u0427\u0442\u043e \u043f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u0442\u0435 \u043f\u0440\u0438 \u0433\u0440\u0435\u0439\u0434\u0438\u043d\u0433\u0435?"}, "options": [
                {"value": "visual_dimensions", "label": {"en": "Surface, color, edges, dimensions", "id": "Permukaan, warna, tepi, dimensi", "ru": "\u041f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u044c, \u0446\u0432\u0435\u0442, \u043a\u0440\u0430\u044f, \u0440\u0430\u0437\u043c\u0435\u0440\u044b"}},
                {"value": "weight", "label": {"en": "Weight only", "id": "Hanya berat", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0432\u0435\u0441"}},
                {"value": "nothing", "label": {"en": "Nothing specific", "id": "Tidak ada yang spesifik", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e \u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u043e\u0433\u043e"}},
            ]},
            {"id": "q2", "question": {"en": "What are the grades?", "id": "Apa grade-nya?", "ru": "\u041a\u0430\u043a\u0438\u0435 \u0433\u0440\u0435\u0439\u0434\u044b?"}, "options": [
                {"value": "a_b_c", "label": {"en": "A, B, C", "id": "A, B, C", "ru": "A, B, C"}},
                {"value": "pass_fail", "label": {"en": "Pass/Fail", "id": "Lolos/Gagal", "ru": "\u041f\u0440\u043e\u0448\u0451\u043b/\u041d\u0435 \u043f\u0440\u043e\u0448\u0451\u043b"}},
                {"value": "numbers", "label": {"en": "1-5 stars", "id": "1-5 bintang", "ru": "1-5 \u0437\u0432\u0451\u0437\u0434"}},
            ]},
            {"id": "q3", "question": {"en": "What to do with borderline tiles?", "id": "Apa yang dilakukan dengan ubin batas?", "ru": "\u0427\u0442\u043e \u0434\u0435\u043b\u0430\u0442\u044c \u0441 \u043f\u043e\u0433\u0440\u0430\u043d\u0438\u0447\u043d\u044b\u043c\u0438?"}, "options": [
                {"value": "qm_decision", "label": {"en": "Consult Quality Manager", "id": "Konsultasikan dengan Manajer Kualitas", "ru": "\u041a\u043e\u043d\u0441\u0443\u043b\u044c\u0442\u0430\u0446\u0438\u044f \u0441 QM"}},
                {"value": "always_a", "label": {"en": "Always grade A", "id": "Selalu grade A", "ru": "\u0412\u0441\u0435\u0433\u0434\u0430 \u0433\u0440\u0435\u0439\u0434 A"}},
                {"value": "discard", "label": {"en": "Discard", "id": "Buang", "ru": "\u0412\u044b\u0431\u0440\u043e\u0441\u0438\u0442\u044c"}},
            ]},
        ],
    },
    "sp_packing": {
        "icon": "\U0001f381",
        "title": {"en": "Packing", "id": "Pengemasan", "ru": "\u0423\u043f\u0430\u043a\u043e\u0432\u043a\u0430"},
        "slides": [
            {"title": {"en": "Packing Standards", "id": "Standar Pengemasan", "ru": "\u0421\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u044b \u0443\u043f\u0430\u043a\u043e\u0432\u043a\u0438"}, "content": {"en": "Pack by order and grade. Use protective materials between tiles. Each box must be labeled with: order number, collection, grade, quantity, tile size. Secure packaging prevents transit damage.", "id": "Kemas berdasarkan pesanan dan grade. Gunakan material pelindung antar ubin. Setiap kotak harus dilabeli.", "ru": "\u0423\u043f\u0430\u043a\u043e\u0432\u043a\u0430 \u043f\u043e \u0437\u0430\u043a\u0430\u0437\u0430\u043c \u0438 \u0433\u0440\u0435\u0439\u0434\u0430\u043c. \u0417\u0430\u0449\u0438\u0442\u043d\u044b\u0439 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b \u043c\u0435\u0436\u0434\u0443 \u043f\u043b\u0438\u0442\u043a\u0430\u043c\u0438. \u041c\u0430\u0440\u043a\u0438\u0440\u043e\u0432\u043a\u0430 \u043a\u0430\u0436\u0434\u043e\u0439 \u043a\u043e\u0440\u043e\u0431\u043a\u0438."}, "icon": "\U0001f4e6"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "How should tiles be packed?", "id": "Bagaimana ubin harus dikemas?", "ru": "\u041a\u0430\u043a \u0443\u043f\u0430\u043a\u043e\u0432\u044b\u0432\u0430\u0442\u044c?"}, "options": [
                {"value": "by_order_grade", "label": {"en": "By order and grade with protective materials", "id": "Berdasarkan pesanan dan grade dengan material pelindung", "ru": "\u041f\u043e \u0437\u0430\u043a\u0430\u0437\u0430\u043c \u0438 \u0433\u0440\u0435\u0439\u0434\u0430\u043c \u0441 \u0437\u0430\u0449\u0438\u0442\u043e\u0439"}},
                {"value": "all_together", "label": {"en": "All together in one box", "id": "Semua dalam satu kotak", "ru": "\u0412\u0441\u0451 \u0432 \u043e\u0434\u043d\u0443 \u043a\u043e\u0440\u043e\u0431\u043a\u0443"}},
                {"value": "no_rules", "label": {"en": "No rules", "id": "Tidak ada aturan", "ru": "\u0411\u0435\u0437 \u043f\u0440\u0430\u0432\u0438\u043b"}},
            ]},
            {"id": "q2", "question": {"en": "Why use protective materials?", "id": "Mengapa gunakan material pelindung?", "ru": "\u0417\u0430\u0447\u0435\u043c \u0437\u0430\u0449\u0438\u0442\u043d\u044b\u0439 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b?"}, "options": [
                {"value": "prevent_damage", "label": {"en": "Prevent transit damage to handcrafted tiles", "id": "Mencegah kerusakan transit pada ubin buatan tangan", "ru": "\u041f\u0440\u0435\u0434\u043e\u0442\u0432\u0440\u0430\u0442\u0438\u0442\u044c \u043f\u043e\u0432\u0440\u0435\u0436\u0434\u0435\u043d\u0438\u044f \u043f\u0440\u0438 \u0442\u0440\u0430\u043d\u0441\u043f\u043e\u0440\u0442\u0438\u0440\u043e\u0432\u043a\u0435"}},
                {"value": "looks", "label": {"en": "Just for looks", "id": "Hanya untuk penampilan", "ru": "\u0414\u043b\u044f \u043a\u0440\u0430\u0441\u043e\u0442\u044b"}},
                {"value": "not_needed", "label": {"en": "Not needed", "id": "Tidak diperlukan", "ru": "\u041d\u0435 \u043d\u0443\u0436\u043d\u043e"}},
            ]},
            {"id": "q3", "question": {"en": "What must each box label include?", "id": "Apa yang harus disertakan pada label kotak?", "ru": "\u0427\u0442\u043e \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u043d\u0430 \u043c\u0430\u0440\u043a\u0438\u0440\u043e\u0432\u043a\u0435?"}, "options": [
                {"value": "label_each_box", "label": {"en": "Order number, collection, grade, quantity, size", "id": "Nomor pesanan, koleksi, grade, jumlah, ukuran", "ru": "\u0417\u0430\u043a\u0430\u0437, \u043a\u043e\u043b\u043b\u0435\u043a\u0446\u0438\u044f, \u0433\u0440\u0435\u0439\u0434, \u043a\u043e\u043b-\u0432\u043e, \u0440\u0430\u0437\u043c\u0435\u0440"}},
                {"value": "nothing", "label": {"en": "No label needed", "id": "Tidak perlu label", "ru": "\u041c\u0430\u0440\u043a\u0438\u0440\u043e\u0432\u043a\u0430 \u043d\u0435 \u043d\u0443\u0436\u043d\u0430"}},
                {"value": "name_only", "label": {"en": "Just product name", "id": "Hanya nama produk", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435"}},
            ]},
        ],
    },
    "sp_photos": {
        "icon": "\U0001f4f8",
        "title": {"en": "Photo Documentation", "id": "Dokumentasi Foto", "ru": "\u0424\u043e\u0442\u043e\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u044f"},
        "slides": [
            {"title": {"en": "When to Photograph", "id": "Kapan Memfoto", "ru": "\u041a\u043e\u0433\u0434\u0430 \u0444\u043e\u0442\u043e\u0433\u0440\u0430\u0444\u0438\u0440\u043e\u0432\u0430\u0442\u044c"}, "content": {"en": "Photograph packed boxes before closing, any unusual tiles, borderline grade decisions. Upload to Telegram bot for documentation. Photos earn bonus points in the gamification system.", "id": "Foto kotak yang sudah dikemas, ubin yang tidak biasa. Unggah ke bot Telegram. Foto mendapat poin bonus.", "ru": "\u0424\u043e\u0442\u043e\u0433\u0440\u0430\u0444\u0438\u0440\u0443\u0439\u0442\u0435 \u0443\u043f\u0430\u043a\u043e\u0432\u0430\u043d\u043d\u044b\u0435 \u043a\u043e\u0440\u043e\u0431\u043a\u0438, \u043d\u0435\u043e\u0431\u044b\u0447\u043d\u044b\u0435 \u043f\u043b\u0438\u0442\u043a\u0438. \u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0432 Telegram \u0434\u0430\u0451\u0442 \u0431\u043e\u043d\u0443\u0441\u043d\u044b\u0435 \u043e\u0447\u043a\u0438."}, "icon": "\U0001f4f7"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "Why take packing photos?", "id": "Mengapa ambil foto pengemasan?", "ru": "\u0417\u0430\u0447\u0435\u043c \u0444\u043e\u0442\u043e \u0443\u043f\u0430\u043a\u043e\u0432\u043a\u0438?"}, "options": [
                {"value": "documentation_proof", "label": {"en": "Documentation and quality proof", "id": "Dokumentasi dan bukti kualitas", "ru": "\u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u044f \u0438 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435"}},
                {"value": "fun", "label": {"en": "For fun", "id": "Untuk kesenangan", "ru": "\u0414\u043b\u044f \u0440\u0430\u0437\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u044f"}},
                {"value": "not_needed", "label": {"en": "Not needed", "id": "Tidak diperlukan", "ru": "\u041d\u0435 \u043d\u0443\u0436\u043d\u043e"}},
            ]},
            {"id": "q2", "question": {"en": "Where to upload photos?", "id": "Di mana mengunggah foto?", "ru": "\u041a\u0443\u0434\u0430 \u0437\u0430\u0433\u0440\u0443\u0436\u0430\u0442\u044c \u0444\u043e\u0442\u043e?"}, "options": [
                {"value": "telegram_bot", "label": {"en": "Telegram bot", "id": "Bot Telegram", "ru": "Telegram-\u0431\u043e\u0442"}},
                {"value": "email", "label": {"en": "Email", "id": "Email", "ru": "Email"}},
                {"value": "usb", "label": {"en": "USB drive", "id": "Flash drive USB", "ru": "USB-\u0444\u043b\u0435\u0448\u043a\u0430"}},
            ]},
            {"id": "q3", "question": {"en": "What do you earn for photos?", "id": "Apa yang Anda dapatkan untuk foto?", "ru": "\u0427\u0442\u043e \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442\u0435 \u0437\u0430 \u0444\u043e\u0442\u043e?"}, "options": [
                {"value": "points_earned", "label": {"en": "Bonus gamification points", "id": "Poin bonus gamifikasi", "ru": "\u0411\u043e\u043d\u0443\u0441\u043d\u044b\u0435 \u043e\u0447\u043a\u0438"}},
                {"value": "nothing", "label": {"en": "Nothing", "id": "Tidak ada", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e"}},
                {"value": "money", "label": {"en": "Cash", "id": "Uang", "ru": "\u0414\u0435\u043d\u044c\u0433\u0438"}},
            ]},
        ],
    },
    "sp_completion": {
        "icon": "\u2705",
        "title": {"en": "Order Completion", "id": "Penyelesaian Pesanan", "ru": "\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u0435 \u0437\u0430\u043a\u0430\u0437\u0430"},
        "slides": [
            {"title": {"en": "Completing the Flow", "id": "Menyelesaikan Alur", "ru": "\u0417\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0438\u0435 \u043f\u043e\u0442\u043e\u043a\u0430"}, "content": {"en": "After packing: update the system with exact counts per grade, notify warehouse that order is ready for shipment. The status changes to 'packed' and warehouse prepares shipping.", "id": "Setelah pengemasan: perbarui sistem dengan jumlah tepat per grade, beritahu gudang bahwa pesanan siap kirim.", "ru": "\u041f\u043e\u0441\u043b\u0435 \u0443\u043f\u0430\u043a\u043e\u0432\u043a\u0438: \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u0435 \u0441\u0438\u0441\u0442\u0435\u043c\u0443 \u0441 \u0442\u043e\u0447\u043d\u044b\u043c\u0438 \u0434\u0430\u043d\u043d\u044b\u043c\u0438, \u0443\u0432\u0435\u0434\u043e\u043c\u0438\u0442\u0435 \u0441\u043a\u043b\u0430\u0434."}, "icon": "\U0001f4e6"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What must you do after packing?", "id": "Apa yang harus dilakukan setelah pengemasan?", "ru": "\u0427\u0442\u043e \u043d\u0443\u0436\u043d\u043e \u043f\u043e\u0441\u043b\u0435 \u0443\u043f\u0430\u043a\u043e\u0432\u043a\u0438?"}, "options": [
                {"value": "system_update", "label": {"en": "Update system with exact counts per grade", "id": "Perbarui sistem dengan jumlah tepat per grade", "ru": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0441\u0438\u0441\u0442\u0435\u043c\u0443 \u0441 \u0442\u043e\u0447\u043d\u044b\u043c\u0438 \u043a\u043e\u043b-\u0432\u0430\u043c\u0438"}},
                {"value": "nothing", "label": {"en": "Nothing", "id": "Tidak ada", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e"}},
                {"value": "email", "label": {"en": "Send email", "id": "Kirim email", "ru": "\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c email"}},
            ]},
            {"id": "q2", "question": {"en": "Who do you notify?", "id": "Siapa yang Anda beritahu?", "ru": "\u041a\u043e\u0433\u043e \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u044f\u0435\u0442\u0435?"}, "options": [
                {"value": "warehouse_notification", "label": {"en": "Warehouse that order is ready for shipment", "id": "Gudang bahwa pesanan siap kirim", "ru": "\u0421\u043a\u043b\u0430\u0434 \u043e \u0433\u043e\u0442\u043e\u0432\u043d\u043e\u0441\u0442\u0438 \u043a \u043e\u0442\u0433\u0440\u0443\u0437\u043a\u0435"}},
                {"value": "ceo", "label": {"en": "CEO directly", "id": "CEO langsung", "ru": "CEO \u043d\u0430\u043f\u0440\u044f\u043c\u0443\u044e"}},
                {"value": "nobody", "label": {"en": "Nobody", "id": "Tidak ada", "ru": "\u041d\u0438\u043a\u043e\u0433\u043e"}},
            ]},
            {"id": "q3", "question": {"en": "What status does the order get?", "id": "Status apa yang didapat pesanan?", "ru": "\u041a\u0430\u043a\u043e\u0439 \u0441\u0442\u0430\u0442\u0443\u0441 \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442 \u0437\u0430\u043a\u0430\u0437?"}, "options": [
                {"value": "ready_for_shipment", "label": {"en": "Ready for shipment", "id": "Siap untuk pengiriman", "ru": "\u0413\u043e\u0442\u043e\u0432 \u043a \u043e\u0442\u0433\u0440\u0443\u0437\u043a\u0435"}},
                {"value": "completed", "label": {"en": "Completed", "id": "Selesai", "ru": "\u0417\u0430\u0432\u0435\u0440\u0448\u0451\u043d"}},
                {"value": "in_production", "label": {"en": "In production", "id": "Dalam produksi", "ru": "\u0412 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0441\u0442\u0432\u0435"}},
            ]},
        ],
    },
}
