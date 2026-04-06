"""Quality Manager onboarding content."""

SECTIONS = [
    "qm_overview", "qm_checklists", "qm_defects", "qm_grinding",
    "qm_photos", "qm_reporting",
]

QUIZ_ANSWERS: dict[str, dict[str, str]] = {
    "qm_overview": {"q1": "pre_kiln_final", "q2": "all_positions", "q3": "digital_checklists"},
    "qm_checklists": {"q1": "engobe_glaze_cracks", "q2": "color_dimensions_defects", "q3": "pass_or_action"},
    "qm_defects": {"q1": "type_severity_photo", "q2": "glaze_product_matrix", "q3": "grinding_refire_scrap"},
    "qm_grinding": {"q1": "surface_polish", "q2": "qm_decision", "q3": "back_to_qc"},
    "qm_photos": {"q1": "evidence_documentation", "q2": "ocr_comparison", "q3": "accuracy_points"},
    "qm_reporting": {"q1": "defect_trends", "q2": "pdf_excel", "q3": "per_collection"},
}

ONBOARDING_CONTENT = {
    "qm_overview": {
        "icon": "\u2705",
        "title": {"en": "Quality Manager Overview", "id": "Ikhtisar Manajer Kualitas", "ru": "\u041e\u0431\u0437\u043e\u0440 \u043c\u0435\u043d\u0435\u0434\u0436\u0435\u0440\u0430 \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430"},
        "slides": [
            {"title": {"en": "Your Role", "id": "Peran Anda", "ru": "\u0412\u0430\u0448\u0430 \u0440\u043e\u043b\u044c"}, "content": {"en": "As Quality Manager, you are the guardian of product excellence. You manage two QC stages: Pre-Kiln (before firing) and Final QC (after firing). Every tile must meet Moonjar's craft standards.", "id": "Sebagai Manajer Kualitas, Anda penjaga keunggulan produk. Anda mengelola dua tahap QC: Pre-Kiln dan Final QC. Setiap ubin harus memenuhi standar kerajinan Moonjar.", "ru": "\u041a\u0430\u043a \u043c\u0435\u043d\u0435\u0434\u0436\u0435\u0440 \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430, \u0432\u044b \u2014 \u0445\u0440\u0430\u043d\u0438\u0442\u0435\u043b\u044c \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430. \u0414\u0432\u0430 \u044d\u0442\u0430\u043f\u0430 QC: Pre-Kiln \u0438 Final QC. \u041a\u0430\u0436\u0434\u0430\u044f \u043f\u043b\u0438\u0442\u043a\u0430 \u0434\u043e\u043b\u0436\u043d\u0430 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u043e\u0432\u0430\u0442\u044c \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u0430\u043c."}, "icon": "\U0001f50d"},
            {"title": {"en": "QC Dashboard", "id": "Dashboard QC", "ru": "\u0414\u0430\u0448\u0431\u043e\u0440\u0434 QC"}, "content": {"en": "Your dashboard shows: positions awaiting QC, defect rate trends, today's inspections queue, grinding decisions pending. Color-coded priority helps focus on urgent items.", "id": "Dashboard Anda menampilkan: posisi menunggu QC, tren tingkat cacat, antrean inspeksi hari ini, keputusan grinding tertunda.", "ru": "\u0414\u0430\u0448\u0431\u043e\u0440\u0434: \u043f\u043e\u0437\u0438\u0446\u0438\u0438 \u043d\u0430 QC, \u0442\u0440\u0435\u043d\u0434\u044b \u0434\u0435\u0444\u0435\u043a\u0442\u043e\u0432, \u043e\u0447\u0435\u0440\u0435\u0434\u044c \u0438\u043d\u0441\u043f\u0435\u043a\u0446\u0438\u0439, \u0440\u0435\u0448\u0435\u043d\u0438\u044f \u043f\u043e \u0448\u043b\u0438\u0444\u043e\u0432\u043a\u0435."}, "icon": "\U0001f4ca"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What are the two QC stages?", "id": "Apa dua tahap QC?", "ru": "\u041a\u0430\u043a\u0438\u0435 \u0434\u0432\u0430 \u044d\u0442\u0430\u043f\u0430 QC?"}, "options": [
                {"value": "pre_kiln_final", "label": {"en": "Pre-Kiln QC and Final QC", "id": "Pre-Kiln QC dan Final QC", "ru": "Pre-Kiln QC \u0438 Final QC"}},
                {"value": "one", "label": {"en": "Only one QC stage", "id": "Hanya satu tahap QC", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043e\u0434\u0438\u043d \u044d\u0442\u0430\u043f"}},
                {"value": "three", "label": {"en": "Three stages", "id": "Tiga tahap", "ru": "\u0422\u0440\u0438 \u044d\u0442\u0430\u043f\u0430"}},
            ]},
            {"id": "q2", "question": {"en": "Which positions need QC?", "id": "Posisi mana yang butuh QC?", "ru": "\u041a\u0430\u043a\u0438\u0435 \u043f\u043e\u0437\u0438\u0446\u0438\u0438 \u043d\u0443\u0436\u0434\u0430\u044e\u0442\u0441\u044f \u0432 QC?"}, "options": [
                {"value": "all_positions", "label": {"en": "All positions before and after firing", "id": "Semua posisi sebelum dan setelah pembakaran", "ru": "\u0412\u0441\u0435 \u043f\u043e\u0437\u0438\u0446\u0438\u0438 \u0434\u043e \u0438 \u043f\u043e\u0441\u043b\u0435 \u043e\u0431\u0436\u0438\u0433\u0430"}},
                {"value": "random", "label": {"en": "Random sampling", "id": "Sampling acak", "ru": "\u0421\u043b\u0443\u0447\u0430\u0439\u043d\u0430\u044f \u0432\u044b\u0431\u043e\u0440\u043a\u0430"}},
                {"value": "none", "label": {"en": "Only when requested", "id": "Hanya saat diminta", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043f\u043e \u0437\u0430\u043f\u0440\u043e\u0441\u0443"}},
            ]},
            {"id": "q3", "question": {"en": "How are QC checks performed?", "id": "Bagaimana pemeriksaan QC dilakukan?", "ru": "\u041a\u0430\u043a \u043f\u0440\u043e\u0432\u043e\u0434\u044f\u0442\u0441\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 QC?"}, "options": [
                {"value": "digital_checklists", "label": {"en": "Digital checklists in the system", "id": "Checklist digital di sistem", "ru": "\u0426\u0438\u0444\u0440\u043e\u0432\u044b\u0435 \u0447\u0435\u043a-\u043b\u0438\u0441\u0442\u044b \u0432 \u0441\u0438\u0441\u0442\u0435\u043c\u0435"}},
                {"value": "paper", "label": {"en": "Paper forms", "id": "Formulir kertas", "ru": "\u0411\u0443\u043c\u0430\u0436\u043d\u044b\u0435 \u0444\u043e\u0440\u043c\u044b"}},
                {"value": "verbal", "label": {"en": "Verbal approval", "id": "Persetujuan verbal", "ru": "\u0423\u0441\u0442\u043d\u043e"}},
            ]},
        ],
    },
    "qm_checklists": {
        "icon": "\U0001f4dd",
        "title": {"en": "QC Checklists", "id": "Checklist QC", "ru": "\u0427\u0435\u043a-\u043b\u0438\u0441\u0442\u044b QC"},
        "slides": [
            {"title": {"en": "Pre-Kiln Checklist", "id": "Checklist Pre-Kiln", "ru": "\u0427\u0435\u043a-\u043b\u0438\u0441\u0442 \u0434\u043e \u043e\u0431\u0436\u0438\u0433\u0430"}, "content": {"en": "Check: engobe coverage (uniform, no bare spots), glaze application (correct thickness, even distribution), no cracks or chips, correct tile dimensions, proper drying state.", "id": "Periksa: cakupan engobe (seragam), aplikasi glasir (ketebalan benar), tidak ada retak, dimensi ubin benar, kondisi pengeringan tepat.", "ru": "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430: \u043f\u043e\u043a\u0440\u044b\u0442\u0438\u0435 \u044d\u043d\u0433\u043e\u0431\u043e\u043c, \u0433\u043b\u0430\u0437\u0443\u0440\u044c (\u0442\u043e\u043b\u0449\u0438\u043d\u0430, \u0440\u0430\u0432\u043d\u043e\u043c\u0435\u0440\u043d\u043e\u0441\u0442\u044c), \u0442\u0440\u0435\u0449\u0438\u043d\u044b, \u0440\u0430\u0437\u043c\u0435\u0440\u044b, \u0441\u0443\u0448\u043a\u0430."}, "icon": "\U0001f50d"},
            {"title": {"en": "Final QC Checklist", "id": "Checklist Final QC", "ru": "\u0427\u0435\u043a-\u043b\u0438\u0441\u0442 \u0444\u0438\u043d\u0430\u043b\u044c\u043d\u043e\u0433\u043e QC"}, "content": {"en": "After firing: color accuracy vs sample, no surface defects (pinholes, crawling, crazing), correct dimensions (no warping), edge quality, overall appearance grade.", "id": "Setelah pembakaran: akurasi warna vs sampel, tidak ada cacat permukaan, dimensi benar, kualitas tepi.", "ru": "\u041f\u043e\u0441\u043b\u0435 \u043e\u0431\u0436\u0438\u0433\u0430: \u0446\u0432\u0435\u0442 vs \u043e\u0431\u0440\u0430\u0437\u0435\u0446, \u0434\u0435\u0444\u0435\u043a\u0442\u044b \u043f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u0438, \u0440\u0430\u0437\u043c\u0435\u0440\u044b, \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u043e \u043a\u0440\u0430\u0451\u0432."}, "icon": "\u2705"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What does Pre-Kiln QC check?", "id": "Apa yang diperiksa Pre-Kiln QC?", "ru": "\u0427\u0442\u043e \u043f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u0442 Pre-Kiln QC?"}, "options": [
                {"value": "engobe_glaze_cracks", "label": {"en": "Engobe coverage, glaze application, cracks", "id": "Cakupan engobe, aplikasi glasir, retak", "ru": "\u042d\u043d\u0433\u043e\u0431, \u0433\u043b\u0430\u0437\u0443\u0440\u044c, \u0442\u0440\u0435\u0449\u0438\u043d\u044b"}},
                {"value": "color_only", "label": {"en": "Color only", "id": "Hanya warna", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0446\u0432\u0435\u0442"}},
                {"value": "weight", "label": {"en": "Weight only", "id": "Hanya berat", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0432\u0435\u0441"}},
            ]},
            {"id": "q2", "question": {"en": "What does Final QC check?", "id": "Apa yang diperiksa Final QC?", "ru": "\u0427\u0442\u043e \u043f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u0442 Final QC?"}, "options": [
                {"value": "color_dimensions_defects", "label": {"en": "Color accuracy, dimensions, surface defects", "id": "Akurasi warna, dimensi, cacat permukaan", "ru": "\u0426\u0432\u0435\u0442, \u0440\u0430\u0437\u043c\u0435\u0440\u044b, \u0434\u0435\u0444\u0435\u043a\u0442\u044b \u043f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u0438"}},
                {"value": "weight", "label": {"en": "Weight only", "id": "Hanya berat", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0432\u0435\u0441"}},
                {"value": "nothing", "label": {"en": "Just visual glance", "id": "Hanya lihat sekilas", "ru": "\u041f\u0440\u043e\u0441\u0442\u043e \u0432\u0437\u0433\u043b\u044f\u0434"}},
            ]},
            {"id": "q3", "question": {"en": "What happens after QC check?", "id": "Apa yang terjadi setelah pemeriksaan QC?", "ru": "\u0427\u0442\u043e \u043f\u043e\u0441\u043b\u0435 QC?"}, "options": [
                {"value": "pass_or_action", "label": {"en": "Pass to finished, or mark for grinding/refire/scrap", "id": "Lolos ke selesai, atau tandai untuk grinding/refire/scrap", "ru": "\u041f\u0440\u043e\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u0438\u043b\u0438 \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043d\u0430 \u0448\u043b\u0438\u0444\u043e\u0432\u043a\u0443/\u043f\u0435\u0440\u0435\u043e\u0431\u0436\u0438\u0433/\u0431\u0440\u0430\u043a"}},
                {"value": "auto", "label": {"en": "Automatic decision", "id": "Keputusan otomatis", "ru": "\u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u043e\u0435 \u0440\u0435\u0448\u0435\u043d\u0438\u0435"}},
                {"value": "wait", "label": {"en": "Wait for PM approval", "id": "Tunggu persetujuan PM", "ru": "\u0416\u0434\u0430\u0442\u044c PM"}},
            ]},
        ],
    },
    "qm_defects": {
        "icon": "\u26a0\ufe0f",
        "title": {"en": "Defect Management", "id": "Manajemen Cacat", "ru": "\u0423\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0434\u0435\u0444\u0435\u043a\u0442\u0430\u043c\u0438"},
        "slides": [
            {"title": {"en": "Logging Defects", "id": "Mencatat Cacat", "ru": "\u0420\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044f \u0434\u0435\u0444\u0435\u043a\u0442\u043e\u0432"}, "content": {"en": "For each defect: log type (pinhole, crawling, crazing, crack, color mismatch), severity (minor/major/critical), take photo. The system builds a defect database for analysis.", "id": "Untuk setiap cacat: catat jenis, tingkat keparahan, ambil foto. Sistem membangun database cacat untuk analisis.", "ru": "\u0414\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u0434\u0435\u0444\u0435\u043a\u0442\u0430: \u0442\u0438\u043f, \u0441\u0442\u0435\u043f\u0435\u043d\u044c, \u0444\u043e\u0442\u043e. \u0421\u0438\u0441\u0442\u0435\u043c\u0430 \u043d\u0430\u043a\u0430\u043f\u043b\u0438\u0432\u0430\u0435\u0442 \u0431\u0430\u0437\u0443 \u0434\u0435\u0444\u0435\u043a\u0442\u043e\u0432 \u0434\u043b\u044f \u0430\u043d\u0430\u043b\u0438\u0437\u0430."}, "icon": "\U0001f4dd"},
            {"title": {"en": "Defect Coefficient Matrix", "id": "Matriks Koefisien Cacat", "ru": "\u041c\u0430\u0442\u0440\u0438\u0446\u0430 \u0434\u0435\u0444\u0435\u043a\u0442\u043e\u0432"}, "content": {"en": "The 2D matrix (glaze type x product type) predicts expected defect rates. This helps plan how many extra tiles to produce. Your QC data directly improves these predictions.", "id": "Matriks 2D (jenis glasir x jenis produk) memprediksi tingkat cacat yang diharapkan. Data QC Anda langsung meningkatkan prediksi ini.", "ru": "2D-\u043c\u0430\u0442\u0440\u0438\u0446\u0430 (\u0433\u043b\u0430\u0437\u0443\u0440\u044c x \u043f\u0440\u043e\u0434\u0443\u043a\u0442) \u043f\u0440\u0435\u0434\u0441\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442 \u043f\u0440\u043e\u0446\u0435\u043d\u0442 \u0431\u0440\u0430\u043a\u0430. \u0412\u0430\u0448\u0438 \u0434\u0430\u043d\u043d\u044b\u0435 QC \u0443\u043b\u0443\u0447\u0448\u0430\u044e\u0442 \u043f\u0440\u043e\u0433\u043d\u043e\u0437\u044b."}, "icon": "\U0001f4d0"},
            {"title": {"en": "Decision Options", "id": "Opsi Keputusan", "ru": "\u0412\u0430\u0440\u0438\u0430\u043d\u0442\u044b \u0440\u0435\u0448\u0435\u043d\u0438\u0439"}, "content": {"en": "For defective tiles you decide: grinding (surface polishing to fix minor issues), refire (fire again to fix glaze defects), or scrap (irreparable damage). Each decision is logged with reason.", "id": "Untuk ubin cacat Anda memutuskan: grinding, refire, atau scrap. Setiap keputusan dicatat dengan alasan.", "ru": "\u0414\u043b\u044f \u0431\u0440\u0430\u043a\u043e\u0432\u0430\u043d\u043d\u044b\u0445 \u043f\u043b\u0438\u0442\u043e\u043a: \u0448\u043b\u0438\u0444\u043e\u0432\u043a\u0430, \u043f\u0435\u0440\u0435\u043e\u0431\u0436\u0438\u0433 \u0438\u043b\u0438 \u0431\u0440\u0430\u043a. \u041a\u0430\u0436\u0434\u043e\u0435 \u0440\u0435\u0448\u0435\u043d\u0438\u0435 \u043b\u043e\u0433\u0438\u0440\u0443\u0435\u0442\u0441\u044f \u0441 \u043f\u0440\u0438\u0447\u0438\u043d\u043e\u0439."}, "icon": "\u2699\ufe0f"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What must you log for each defect?", "id": "Apa yang harus dicatat untuk setiap cacat?", "ru": "\u0427\u0442\u043e \u043d\u0443\u0436\u043d\u043e \u043b\u043e\u0433\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u0434\u0435\u0444\u0435\u043a\u0442\u0430?"}, "options": [
                {"value": "type_severity_photo", "label": {"en": "Type, severity, and photo", "id": "Jenis, keparahan, dan foto", "ru": "\u0422\u0438\u043f, \u0441\u0442\u0435\u043f\u0435\u043d\u044c \u0438 \u0444\u043e\u0442\u043e"}},
                {"value": "just_type", "label": {"en": "Just the type", "id": "Hanya jenisnya", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0442\u0438\u043f"}},
                {"value": "nothing", "label": {"en": "Nothing, just reject it", "id": "Tidak ada, tolak saja", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e, \u043f\u0440\u043e\u0441\u0442\u043e \u043e\u0442\u043a\u043b\u043e\u043d\u0438\u0442\u044c"}},
            ]},
            {"id": "q2", "question": {"en": "What predicts defect rates?", "id": "Apa yang memprediksi tingkat cacat?", "ru": "\u0427\u0442\u043e \u043f\u0440\u0435\u0434\u0441\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442 \u043f\u0440\u043e\u0446\u0435\u043d\u0442 \u0431\u0440\u0430\u043a\u0430?"}, "options": [
                {"value": "glaze_product_matrix", "label": {"en": "2D matrix of glaze type x product type", "id": "Matriks 2D jenis glasir x jenis produk", "ru": "2D-\u043c\u0430\u0442\u0440\u0438\u0446\u0430 \u0433\u043b\u0430\u0437\u0443\u0440\u044c x \u043f\u0440\u043e\u0434\u0443\u043a\u0442"}},
                {"value": "random", "label": {"en": "Random estimation", "id": "Estimasi acak", "ru": "\u0421\u043b\u0443\u0447\u0430\u0439\u043d\u0430\u044f \u043e\u0446\u0435\u043d\u043a\u0430"}},
                {"value": "fixed", "label": {"en": "Fixed 5% for all", "id": "5% tetap untuk semua", "ru": "\u0424\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0435 5%"}},
            ]},
            {"id": "q3", "question": {"en": "What options for defective tiles?", "id": "Opsi untuk ubin cacat?", "ru": "\u0412\u0430\u0440\u0438\u0430\u043d\u0442\u044b \u0434\u043b\u044f \u0431\u0440\u0430\u043a\u043e\u0432\u0430\u043d\u043d\u044b\u0445 \u043f\u043b\u0438\u0442\u043e\u043a?"}, "options": [
                {"value": "grinding_refire_scrap", "label": {"en": "Grinding, refire, or scrap", "id": "Grinding, refire, atau scrap", "ru": "\u0428\u043b\u0438\u0444\u043e\u0432\u043a\u0430, \u043f\u0435\u0440\u0435\u043e\u0431\u0436\u0438\u0433 \u0438\u043b\u0438 \u0431\u0440\u0430\u043a"}},
                {"value": "scrap_only", "label": {"en": "Scrap only", "id": "Hanya scrap", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0431\u0440\u0430\u043a"}},
                {"value": "ship_anyway", "label": {"en": "Ship anyway", "id": "Kirim saja", "ru": "\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043a\u0430\u043a \u0435\u0441\u0442\u044c"}},
            ]},
        ],
    },
    "qm_grinding": {
        "icon": "\U0001f6e0\ufe0f",
        "title": {"en": "Grinding Decisions", "id": "Keputusan Grinding", "ru": "\u0420\u0435\u0448\u0435\u043d\u0438\u044f \u043f\u043e \u0448\u043b\u0438\u0444\u043e\u0432\u043a\u0435"},
        "slides": [
            {"title": {"en": "When to Grind", "id": "Kapan Grinding", "ru": "\u041a\u043e\u0433\u0434\u0430 \u0448\u043b\u0438\u0444\u043e\u0432\u0430\u0442\u044c"}, "content": {"en": "Grinding fixes surface irregularities: minor glaze bumps, small pinholes, slight edge roughness. Not suitable for color issues, deep cracks, or warping.", "id": "Grinding memperbaiki ketidakrataan permukaan: tonjolan glasir kecil, pinholes kecil. Tidak cocok untuk masalah warna atau retak dalam.", "ru": "\u0428\u043b\u0438\u0444\u043e\u0432\u043a\u0430 \u0438\u0441\u043f\u0440\u0430\u0432\u043b\u044f\u0435\u0442 \u043d\u0435\u0440\u043e\u0432\u043d\u043e\u0441\u0442\u0438 \u043f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u0438. \u041d\u0435 \u043f\u043e\u0434\u0445\u043e\u0434\u0438\u0442 \u0434\u043b\u044f \u0446\u0432\u0435\u0442\u043e\u0432\u044b\u0445 \u043f\u0440\u043e\u0431\u043b\u0435\u043c \u0438\u043b\u0438 \u0433\u043b\u0443\u0431\u043e\u043a\u0438\u0445 \u0442\u0440\u0435\u0449\u0438\u043d."}, "icon": "\U0001f527"},
            {"title": {"en": "After Grinding", "id": "Setelah Grinding", "ru": "\u041f\u043e\u0441\u043b\u0435 \u0448\u043b\u0438\u0444\u043e\u0432\u043a\u0438"}, "content": {"en": "After grinding, tiles go back through QC for re-inspection. If they pass, they move to finished goods. If not, they may need refire or be scrapped.", "id": "Setelah grinding, ubin kembali ke QC untuk inspeksi ulang. Jika lolos, pindah ke barang jadi.", "ru": "\u041f\u043e\u0441\u043b\u0435 \u0448\u043b\u0438\u0444\u043e\u0432\u043a\u0438 \u043f\u043b\u0438\u0442\u043a\u0438 \u0432\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u044e\u0442\u0441\u044f \u043d\u0430 QC. \u0415\u0441\u043b\u0438 \u043f\u0440\u043e\u0448\u043b\u0438 \u2014 \u0433\u043e\u0442\u043e\u0432\u0430\u044f \u043f\u0440\u043e\u0434\u0443\u043a\u0446\u0438\u044f."}, "icon": "\U0001f504"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What does grinding fix?", "id": "Apa yang diperbaiki grinding?", "ru": "\u0427\u0442\u043e \u0438\u0441\u043f\u0440\u0430\u0432\u043b\u044f\u0435\u0442 \u0448\u043b\u0438\u0444\u043e\u0432\u043a\u0430?"}, "options": [
                {"value": "surface_polish", "label": {"en": "Surface irregularities and minor defects", "id": "Ketidakrataan permukaan dan cacat kecil", "ru": "\u041d\u0435\u0440\u043e\u0432\u043d\u043e\u0441\u0442\u0438 \u043f\u043e\u0432\u0435\u0440\u0445\u043d\u043e\u0441\u0442\u0438"}},
                {"value": "color", "label": {"en": "Color issues", "id": "Masalah warna", "ru": "\u041f\u0440\u043e\u0431\u043b\u0435\u043c\u044b \u0446\u0432\u0435\u0442\u0430"}},
                {"value": "everything", "label": {"en": "All types of defects", "id": "Semua jenis cacat", "ru": "\u0412\u0441\u0435 \u0434\u0435\u0444\u0435\u043a\u0442\u044b"}},
            ]},
            {"id": "q2", "question": {"en": "Who makes the grinding decision?", "id": "Siapa yang membuat keputusan grinding?", "ru": "\u041a\u0442\u043e \u043f\u0440\u0438\u043d\u0438\u043c\u0430\u0435\u0442 \u0440\u0435\u0448\u0435\u043d\u0438\u0435 \u043e \u0448\u043b\u0438\u0444\u043e\u0432\u043a\u0435?"}, "options": [
                {"value": "qm_decision", "label": {"en": "Quality Manager", "id": "Manajer Kualitas", "ru": "\u041c\u0435\u043d\u0435\u0434\u0436\u0435\u0440 \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430"}},
                {"value": "auto", "label": {"en": "Automatic", "id": "Otomatis", "ru": "\u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438"}},
                {"value": "pm", "label": {"en": "Production Manager", "id": "Manajer Produksi", "ru": "PM"}},
            ]},
            {"id": "q3", "question": {"en": "What happens after grinding?", "id": "Apa yang terjadi setelah grinding?", "ru": "\u0427\u0442\u043e \u043f\u043e\u0441\u043b\u0435 \u0448\u043b\u0438\u0444\u043e\u0432\u043a\u0438?"}, "options": [
                {"value": "back_to_qc", "label": {"en": "Back to QC for re-inspection", "id": "Kembali ke QC untuk inspeksi ulang", "ru": "\u041d\u0430\u0437\u0430\u0434 \u043d\u0430 QC \u0434\u043b\u044f \u043f\u043e\u0432\u0442\u043e\u0440\u043d\u043e\u0439 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438"}},
                {"value": "finished", "label": {"en": "Straight to finished goods", "id": "Langsung ke barang jadi", "ru": "\u0421\u0440\u0430\u0437\u0443 \u0432 \u0433\u043e\u0442\u043e\u0432\u0443\u044e \u043f\u0440\u043e\u0434\u0443\u043a\u0446\u0438\u044e"}},
                {"value": "scrap", "label": {"en": "Always scrapped after", "id": "Selalu di-scrap setelahnya", "ru": "\u0412\u0441\u0435\u0433\u0434\u0430 \u0431\u0440\u0430\u043a"}},
            ]},
        ],
    },
    "qm_photos": {
        "icon": "\U0001f4f8",
        "title": {"en": "Photo Documentation", "id": "Dokumentasi Foto", "ru": "\u0424\u043e\u0442\u043e\u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u044f"},
        "slides": [
            {"title": {"en": "Why Photos Matter", "id": "Mengapa Foto Penting", "ru": "\u0417\u0430\u0447\u0435\u043c \u0444\u043e\u0442\u043e"}, "content": {"en": "Photos provide evidence for defect tracking, customer disputes, and process improvement. Every defect should be photographed. The Telegram bot supports photo upload with OCR.", "id": "Foto memberikan bukti untuk pelacakan cacat, sengketa pelanggan, dan perbaikan proses. Setiap cacat harus difoto.", "ru": "\u0424\u043e\u0442\u043e \u2014 \u0434\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u0430 \u0434\u043b\u044f \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u044f, \u0441\u043f\u043e\u0440\u043e\u0432, \u0443\u043b\u0443\u0447\u0448\u0435\u043d\u0438\u044f \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u043e\u0432. \u041a\u0430\u0436\u0434\u044b\u0439 \u0434\u0435\u0444\u0435\u043a\u0442 \u043d\u0443\u0436\u043d\u043e \u0444\u043e\u0442\u043e\u0433\u0440\u0430\u0444\u0438\u0440\u043e\u0432\u0430\u0442\u044c."}, "icon": "\U0001f4f7"},
            {"title": {"en": "Recipe Verification via Photo", "id": "Verifikasi Resep via Foto", "ru": "\u0412\u0435\u0440\u0438\u0444\u0438\u043a\u0430\u0446\u0438\u044f \u0440\u0435\u0446\u0435\u043f\u0442\u043e\u0432 \u043f\u043e \u0444\u043e\u0442\u043e"}, "content": {"en": "Send recipe card photos to the Telegram bot. OCR reads the data, compares with the spec in the database, calculates accuracy, and awards points. This gamifies quality control.", "id": "Kirim foto kartu resep ke bot Telegram. OCR membaca data, membandingkan dengan spek, menghitung akurasi, memberikan poin.", "ru": "\u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0444\u043e\u0442\u043e \u0440\u0435\u0446\u0435\u043f\u0442\u0443\u0440\u043d\u043e\u0439 \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0438 \u0431\u043e\u0442\u0443. OCR \u0441\u0440\u0430\u0432\u043d\u0438\u0442 \u0441\u043e \u0441\u043f\u0435\u043a\u043e\u0439, \u043d\u0430\u0447\u0438\u0441\u043b\u0438\u0442 \u043e\u0447\u043a\u0438."}, "icon": "\U0001f916"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "Why should you photograph defects?", "id": "Mengapa harus memfoto cacat?", "ru": "\u0417\u0430\u0447\u0435\u043c \u0444\u043e\u0442\u043e\u0433\u0440\u0430\u0444\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0434\u0435\u0444\u0435\u043a\u0442\u044b?"}, "options": [
                {"value": "evidence_documentation", "label": {"en": "Evidence for tracking, disputes, and improvement", "id": "Bukti untuk pelacakan, sengketa, dan perbaikan", "ru": "\u0414\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u0430 \u0434\u043b\u044f \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u043d\u0438\u044f \u0438 \u0443\u043b\u0443\u0447\u0448\u0435\u043d\u0438\u0439"}},
                {"value": "decoration", "label": {"en": "For social media", "id": "Untuk media sosial", "ru": "\u0414\u043b\u044f \u0441\u043e\u0446\u0441\u0435\u0442\u0435\u0439"}},
                {"value": "not_needed", "label": {"en": "Not needed", "id": "Tidak diperlukan", "ru": "\u041d\u0435 \u043d\u0443\u0436\u043d\u043e"}},
            ]},
            {"id": "q2", "question": {"en": "What does OCR do with recipe photos?", "id": "Apa yang dilakukan OCR dengan foto resep?", "ru": "\u0427\u0442\u043e OCR \u0434\u0435\u043b\u0430\u0435\u0442 \u0441 \u0444\u043e\u0442\u043e \u0440\u0435\u0446\u0435\u043f\u0442\u043e\u0432?"}, "options": [
                {"value": "ocr_comparison", "label": {"en": "Reads data, compares with spec, scores accuracy", "id": "Membaca data, membandingkan dengan spek, menilai akurasi", "ru": "\u0427\u0438\u0442\u0430\u0435\u0442, \u0441\u0440\u0430\u0432\u043d\u0438\u0432\u0430\u0435\u0442 \u0441\u043e \u0441\u043f\u0435\u043a\u043e\u0439, \u043e\u0446\u0435\u043d\u0438\u0432\u0430\u0435\u0442 \u0442\u043e\u0447\u043d\u043e\u0441\u0442\u044c"}},
                {"value": "stores", "label": {"en": "Just stores the image", "id": "Hanya menyimpan gambar", "ru": "\u041f\u0440\u043e\u0441\u0442\u043e \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u0442"}},
                {"value": "nothing", "label": {"en": "Nothing", "id": "Tidak ada", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e"}},
            ]},
            {"id": "q3", "question": {"en": "What do you earn for accurate recipes?", "id": "Apa yang Anda dapatkan untuk resep akurat?", "ru": "\u0427\u0442\u043e \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442\u0435 \u0437\u0430 \u0442\u043e\u0447\u043d\u044b\u0435 \u0440\u0435\u0446\u0435\u043f\u0442\u044b?"}, "options": [
                {"value": "accuracy_points", "label": {"en": "Accuracy points (1-10 based on deviation)", "id": "Poin akurasi (1-10 berdasarkan penyimpangan)", "ru": "\u041e\u0447\u043a\u0438 \u0442\u043e\u0447\u043d\u043e\u0441\u0442\u0438 (1-10 \u043f\u043e \u043e\u0442\u043a\u043b\u043e\u043d\u0435\u043d\u0438\u044e)"}},
                {"value": "nothing", "label": {"en": "Nothing", "id": "Tidak ada", "ru": "\u041d\u0438\u0447\u0435\u0433\u043e"}},
                {"value": "money", "label": {"en": "Cash bonus", "id": "Bonus uang", "ru": "\u0414\u0435\u043d\u0435\u0436\u043d\u044b\u0439 \u0431\u043e\u043d\u0443\u0441"}},
            ]},
        ],
    },
    "qm_reporting": {
        "icon": "\U0001f4ca",
        "title": {"en": "QC Reporting", "id": "Pelaporan QC", "ru": "\u041e\u0442\u0447\u0451\u0442\u043d\u043e\u0441\u0442\u044c QC"},
        "slides": [
            {"title": {"en": "Defect Analytics", "id": "Analitik Cacat", "ru": "\u0410\u043d\u0430\u043b\u0438\u0442\u0438\u043a\u0430 \u0434\u0435\u0444\u0435\u043a\u0442\u043e\u0432"}, "content": {"en": "Track defect rates over time by collection, glaze, product type. Identify problematic combinations. Spot trends early to adjust production processes.", "id": "Lacak tingkat cacat berdasarkan koleksi, glasir, jenis produk. Identifikasi kombinasi bermasalah.", "ru": "\u041e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u0439\u0442\u0435 \u0434\u0435\u0444\u0435\u043a\u0442\u044b \u043f\u043e \u043a\u043e\u043b\u043b\u0435\u043a\u0446\u0438\u044f\u043c, \u0433\u043b\u0430\u0437\u0443\u0440\u044f\u043c, \u043f\u0440\u043e\u0434\u0443\u043a\u0442\u0430\u043c. \u041d\u0430\u0445\u043e\u0434\u0438\u0442\u0435 \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u043d\u044b\u0435 \u043a\u043e\u043c\u0431\u0438\u043d\u0430\u0446\u0438\u0438."}, "icon": "\U0001f4c8"},
            {"title": {"en": "Export Reports", "id": "Ekspor Laporan", "ru": "\u042d\u043a\u0441\u043f\u043e\u0440\u0442 \u043e\u0442\u0447\u0451\u0442\u043e\u0432"}, "content": {"en": "Export QC reports as PDF or Excel. Include defect photos, statistics, trends. Share with CEO and production team for improvement discussions.", "id": "Ekspor laporan QC sebagai PDF atau Excel. Sertakan foto cacat, statistik, tren.", "ru": "\u042d\u043a\u0441\u043f\u043e\u0440\u0442 QC-\u043e\u0442\u0447\u0451\u0442\u043e\u0432 \u0432 PDF/Excel \u0441 \u0444\u043e\u0442\u043e, \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u043e\u0439, \u0442\u0440\u0435\u043d\u0434\u0430\u043c\u0438."}, "icon": "\U0001f4e4"},
        ],
        "quiz": [
            {"id": "q1", "question": {"en": "What can you analyze in QC reports?", "id": "Apa yang bisa dianalisis dalam laporan QC?", "ru": "\u0427\u0442\u043e \u043c\u043e\u0436\u043d\u043e \u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0432 \u043e\u0442\u0447\u0451\u0442\u0430\u0445 QC?"}, "options": [
                {"value": "defect_trends", "label": {"en": "Defect trends by collection, glaze, product type", "id": "Tren cacat berdasarkan koleksi, glasir, jenis produk", "ru": "\u0422\u0440\u0435\u043d\u0434\u044b \u0434\u0435\u0444\u0435\u043a\u0442\u043e\u0432 \u043f\u043e \u043a\u043e\u043b\u043b\u0435\u043a\u0446\u0438\u044f\u043c, \u0433\u043b\u0430\u0437\u0443\u0440\u044f\u043c, \u043f\u0440\u043e\u0434\u0443\u043a\u0442\u0430\u043c"}},
                {"value": "nothing", "label": {"en": "No analytics available", "id": "Tidak ada analitik", "ru": "\u0410\u043d\u0430\u043b\u0438\u0442\u0438\u043a\u0430 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430"}},
                {"value": "total_only", "label": {"en": "Only total count", "id": "Hanya total jumlah", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u043e\u0431\u0449\u0435\u0435 \u043a\u043e\u043b-\u0432\u043e"}},
            ]},
            {"id": "q2", "question": {"en": "Export formats?", "id": "Format ekspor?", "ru": "\u0424\u043e\u0440\u043c\u0430\u0442\u044b \u044d\u043a\u0441\u043f\u043e\u0440\u0442\u0430?"}, "options": [
                {"value": "pdf_excel", "label": {"en": "PDF and Excel", "id": "PDF dan Excel", "ru": "PDF \u0438 Excel"}},
                {"value": "csv", "label": {"en": "CSV only", "id": "Hanya CSV", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e CSV"}},
                {"value": "none", "label": {"en": "No export", "id": "Tidak ada ekspor", "ru": "\u041d\u0435\u0442 \u044d\u043a\u0441\u043f\u043e\u0440\u0442\u0430"}},
            ]},
            {"id": "q3", "question": {"en": "How are defects tracked over time?", "id": "Bagaimana cacat dilacak seiring waktu?", "ru": "\u041a\u0430\u043a \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u044e\u0442\u0441\u044f \u0434\u0435\u0444\u0435\u043a\u0442\u044b?"}, "options": [
                {"value": "per_collection", "label": {"en": "Per collection, glaze, and product type with trends", "id": "Per koleksi, glasir, dan jenis produk dengan tren", "ru": "\u041f\u043e \u043a\u043e\u043b\u043b\u0435\u043a\u0446\u0438\u044f\u043c, \u0433\u043b\u0430\u0437\u0443\u0440\u044f\u043c, \u043f\u0440\u043e\u0434\u0443\u043a\u0442\u0430\u043c \u0441 \u0442\u0440\u0435\u043d\u0434\u0430\u043c\u0438"}},
                {"value": "not_tracked", "label": {"en": "Not tracked", "id": "Tidak dilacak", "ru": "\u041d\u0435 \u043e\u0442\u0441\u043b\u0435\u0436\u0438\u0432\u0430\u044e\u0442\u0441\u044f"}},
                {"value": "manual", "label": {"en": "Manual logging only", "id": "Hanya pencatatan manual", "ru": "\u0422\u043e\u043b\u044c\u043a\u043e \u0432\u0440\u0443\u0447\u043d\u0443\u044e"}},
            ]},
        ],
    },
}
