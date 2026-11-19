"""Repeatable Persian sample dataset; all policy values are demo assumptions."""

from __future__ import annotations

from datetime import timedelta

from app import play_data as p

PEOPLE = (
    ("ali", "رضایی", "علی رضایی", "تهران شمال", "مریم", "آرین"),
    ("mina", "احمدی", "مینا احمدی", "البرز", "محمد", "رها"),
    ("sara", "محمدی", "سارا محمدی", "تهران غرب", "پارسا", "نیکا"),
    ("reza", "اسدی", "رضا اسدی", "اصفهان", "آوا", "مانی"),
    ("nahid", "صادقی", "ناهید صادقی", "فارس", "مهرداد", "هانا"),
    ("omid", "حسینی", "امید حسینی", "گیلان", "لاله", "رایان"),
    ("shima", "مرادی", "شیما مرادی", "خراسان رضوی", "علیار", "یلدا"),
    ("kamran", "کاظمی", "کامران کاظمی", "مازندران", "بیتا", "آرش"),
    ("leila", "جعفری", "لیلا جعفری", "تهران شمال", "یاسمن", "نورا"),
    ("navid", "هاشمی", "نوید هاشمی", "البرز", "آیدا", "کیان"),
)

CARD_BANK = {
    "customer": (
        ("خلبانِ بادبادک", "سبکی و رنگ‌های شاد برایش از هر چیز مهم‌تر است."),
        ("آشپزِ ماه", "به دنبال چیزی است که در آشپزخانهٔ کم‌جاذبه‌اش کار کند."),
        ("کتابدارِ پنجره‌نشین", "عاشق داستان است و حسابی به آرامش اهمیت می‌دهد."),
        ("باغبانِ بیابان", "چیزی می‌خواهد که در روزهای گرم همراهش باشد."),
        ("نقاشِ فصل‌ها", "به پیشنهادهایی با رنگ‌های تازه و ایده‌های عجیب علاقه دارد."),
        ("دوچرخه‌سوارِ کوهستان", "برای مسیرهای طولانی وسیله‌ای سبک و کاربردی می‌خواهد."),
    ),
    "product": (
        ("قمقمه", "همراه همیشگی سفر"),
        ("چتر", "پناهی برای روزهای بارانی"),
        ("کوله‌پشتی", "جایی برای چیزهای ضروری"),
        ("چراغ‌قوه", "یک نور کوچک و قابل‌حمل"),
        ("کفش", "برای ماجراجویی‌های دور و نزدیک"),
        ("جعبهٔ ناهار", "یک وعده همیشه همراهت"),
        ("دفترچه", "کاغذ برای ایده‌های تازه"),
        ("ساعت", "قرارها را فراموش نکن"),
        ("عینک", "نگاهی تازه به اطراف"),
        ("گلدان", "خانه‌ای برای یک گیاه"),
        ("بادبادک", "یک پرواز رنگارنگ"),
        ("کلاه", "سایه‌بان شخصی"),
        ("جوراب", "همراه یک مسیر گرم"),
        ("فلاسک", "دما را نگه می‌دارد"),
        ("کارت‌پستال", "برای یک سلام از راه دور"),
        ("زنگ دوچرخه", "خبر از یک سفر کوتاه"),
    ),
    "feature": (
        ("با نور خورشید شارژ می‌شود", "از آفتاب انرژی می‌گیرد."),
        ("رنگ عوض می‌کند", "با هر تغییر هوا رنگ تازه‌ای دارد."),
        ("ضدآب است", "از آب نمی‌ترسد."),
        ("جمع‌شونده است", "در یک جیب کوچک جا می‌شود."),
        ("روی آب می‌ماند", "حتی با موج هم غرق نمی‌شود."),
        ("با لمس روشن می‌شود", "نیازی به دکمه ندارد."),
        ("با خنده راه می‌افتد", "صدای خنده را تشخیص می‌دهد."),
        ("باران را پیش‌بینی می‌کند", "پیش از اولین قطره خبر می‌دهد."),
        ("خودش مرتب می‌شود", "بعد از استفاده به شکل اول برمی‌گردد."),
        ("بوی پرتقال می‌دهد", "رایحه‌اش همیشه تازه است."),
        ("دما را ثابت نگه می‌دارد", "سرما و گرما روی آن اثر ندارد."),
        ("در شب می‌درخشد", "بدون باتری هم پیدا می‌شود."),
        ("صدا را کم می‌کند", "اطرافش آرام‌تر می‌شود."),
        ("دو حالت دارد", "سریع به کاربرد دوم تبدیل می‌شود."),
        ("نام صاحبش را می‌داند", "یک همراه شخصی واقعی است."),
        ("واژه‌ها را می‌خواند", "متن را با صدای ملایم می‌خواند."),
    ),
    "limitation": (
        ("بی‌صدا", "محصول نباید صدا تولید کند."),
        ("بدون برق", "برق در دسترس نیست."),
        ("در یک دست جا شود", "از یک کف دست بزرگ‌تر نباشد."),
        ("با مواد بازیافتی", "مواد اولیه باید بازیافتی باشند."),
        ("فقط یک رنگ", "برای ساخت فقط یک رنگ مجاز است."),
        ("کم‌وزن", "وزن آن نباید از یک سیب بیشتر باشد."),
        ("بدون پلاستیک", "بسته‌بندی و محصول نباید پلاستیک داشته باشند."),
        ("آماده در یک دقیقه", "راه‌اندازی باید خیلی سریع باشد."),
    ),
    "event": (
        ("یک بادِ بازیگوش", "یک باد ناگهانی همه چیز را جابه‌جا کرده است."),
        ("بازار شبانه", "محصول را فقط در تاریکی معرفی می‌کنی."),
        ("مهمان ناخوانده", "یک گربهٔ بازیگوش وسط نمایش پیدایش می‌شود."),
        ("کمبود جا", "تمام غرفه به‌اندازهٔ یک سینی کوچک شده است."),
        ("روز بدون ماشین", "همه‌چیز باید پیاده حمل شود."),
        ("بارانِ بهاری", "راهنمای محصول نباید خیس شود."),
        ("قطع برق", "برق قطع شد؛ محصول باید باز هم مفید باشد."),
        ("جشن رنگ‌ها", "بازار پر از رنگ و جشن است؛ مشتری سخت‌تر متوجه می‌شود."),
    ),
}

QUESTION_BANK = (
    (
        "بزرگ‌ترین سیارهٔ منظومهٔ خورشیدی کدام است؟",
        "علوم و طبیعت",
        "easy",
        ("زمین", "مریخ", "مشتری", "زهره"),
        2,
    ),
    (
        "گیاهان برای فتوسنتز بیشتر از کدام انرژی استفاده می‌کنند؟",
        "علوم و طبیعت",
        "easy",
        ("نور خورشید", "صدا", "باد", "امواج دریا"),
        0,
    ),
    ("کدام جانور پستاندار است؟", "علوم و طبیعت", "easy", ("کوسه", "دلفین", "قورباغه", "طوطی"), 1),
    (
        "در اتمسفر زمین کدام گاز فراوان‌تر است؟",
        "علوم و طبیعت",
        "medium",
        ("اکسیژن", "نیتروژن", "هیدروژن", "هلیوم"),
        1,
    ),
    (
        "به تبدیل مستقیم جامد به گاز چه می‌گویند؟",
        "علوم و طبیعت",
        "hard",
        ("انجماد", "ذوب", "تصعید", "میعان"),
        2,
    ),
    (
        "سبک‌ترین عنصر جدول تناوبی چیست؟",
        "علوم و طبیعت",
        "hard",
        ("هیدروژن", "هلیوم", "لیتیوم", "کربن"),
        0,
    ),
    (
        "حافظ در کدام شهر آرامگاه دارد؟",
        "ایران و فرهنگ",
        "easy",
        ("شیراز", "مشهد", "تبریز", "همدان"),
        0,
    ),
    ("کدام جشن در آغاز بهار است؟", "ایران و فرهنگ", "easy", ("یلدا", "سده", "نوروز", "مهرگان"), 2),
    (
        "نام سرایندهٔ شاهنامه چیست؟",
        "ایران و فرهنگ",
        "medium",
        ("سعدی", "مولوی", "عطار", "فردوسی"),
        3,
    ),
    ("پل خواجو در کدام شهر است؟", "ایران و فرهنگ", "medium", ("یزد", "اصفهان", "کرمان", "رشت"), 1),
    (
        "آرامگاه نادرشاه در کدام شهر است؟",
        "ایران و فرهنگ",
        "hard",
        ("مشهد", "قزوین", "تبریز", "اردبیل"),
        0,
    ),
    (
        "کدام سنگ‌نوشته به سه زبان باستانی نوشته شده است؟",
        "ایران و فرهنگ",
        "hard",
        ("بیستون", "شوشتر", "هگمتانه", "سیلک"),
        0,
    ),
    ("در شطرنج هر طرف چند مهره دارد؟", "سرگرمی و ورزش", "easy", ("۸", "۱۲", "۱۶", "۲۰"), 2),
    ("داخل زمین والیبال هر تیم چند بازیکن دارد؟", "سرگرمی و ورزش", "easy", ("۴", "۵", "۶", "۷"), 2),
    (
        "کدام ساز در گروه سازهای زهی قرار دارد؟",
        "سرگرمی و ورزش",
        "medium",
        ("نی", "تنبک", "تار", "دف"),
        2,
    ),
    (
        "در بسکتبال حرفه‌ای پنج بازیکن یک تیم در کجا هستند؟",
        "سرگرمی و ورزش",
        "medium",
        ("هم‌زمان در زمین", "هم‌زمان روی نیمکت", "تا زمان استراحت بیرون", "فقط در دفاع"),
        0,
    ),
    (
        "مسافت تقریبی دوی ماراتن چند کیلومتر است؟",
        "سرگرمی و ورزش",
        "hard",
        ("۲۰", "۳۰", "۴۲", "۵۷"),
        2,
    ),
    (
        "اصطلاح «کیش» در کدام بازی به کار می‌رود؟",
        "سرگرمی و ورزش",
        "easy",
        ("شطرنج", "تنیس", "والیبال", "بدمینتون"),
        0,
    ),
)

WORD_BANK = (
    ("بادبادک", "با نخ در هوای بادی پرواز می‌کند.", "سرگرمی", ("باد", "نخ", "پرواز")),
    ("فانوس", "برای روشن‌کردن راه در تاریکی به کار می‌رود.", "اشیا", ("چراغ", "روشن", "نور")),
    ("هندوانه", "میوه‌ای با پوست سبز و درون قرمز.", "خوراکی", ("قرمز", "میوه", "یلدا")),
    ("گنجشک", "پرندهٔ کوچک و آشنای کوچه‌ها.", "طبیعت", ("پرنده", "کوچک", "جیک")),
    ("گلخانه", "جایی برای پرورش گیاهان در شرایط کنترل‌شده.", "طبیعت", ("گیاه", "شیشه", "گل")),
    ("دوچرخه", "وسیله‌ای که با پدال جلو می‌رود.", "اشیا", ("چرخ", "پدال", "رکاب")),
    ("کتابخانه", "جایی برای خواندن و امانت گرفتن.", "سرگرمی", ("کتاب", "قفسه", "خواندن")),
    ("آبشار", "آب را یک‌باره از ارتفاع به پایین می‌ریزد.", "طبیعت", ("آب", "کوه", "ارتفاع")),
    ("گردو", "مغزی خوراکی که پوست سختی دارد.", "خوراکی", ("مغز", "پوست", "درخت")),
    ("تلسکوپ", "با آن می‌توان آسمان شب را از نزدیک‌تر دید.", "اشیا", ("ستاره", "دوربین", "عدسی")),
    ("زنبور", "حشره‌ای که به ساختن عسل معروف است.", "طبیعت", ("حشره", "عسل", "کندوی")),
    (
        "کمانچه",
        "سازی که آرشه دارد و هنگام نواختن عمودی نگه‌داشته می‌شود.",
        "سرگرمی",
        ("ساز", "آرشه", "موسیقی"),
    ),
)


def seed(conn) -> None:
    today = p.day()
    moment = p.now()
    month_start, _ = p.month_bounds(today)
    stamp = lambda offset: max(month_start, today + timedelta(days=offset)).isoformat()  # noqa: E731
    date = lambda offset: (today + timedelta(days=offset)).isoformat()  # noqa: E731
    avatars = tuple(p.AVATARS)
    conn.executemany(
        "INSERT INTO play_meta VALUES (?,?)",
        (("isolation", "kilos-play-demo"), ("seeded_at", str(moment))),
    )
    conn.execute(
        """INSERT INTO play_accounts (id,role,name,avatar,created_at)
        VALUES (?,'admin','نگار تهرانی','owl',?)""",
        (p.ADMIN, moment),
    )
    conn.execute("INSERT INTO play_token_rules VALUES (1,1000000,2,?,?)", (moment, p.ADMIN))
    conn.executemany(
        "INSERT INTO play_games VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            (
                "shir",
                "شیر و مرغ کیلوس",
                "با کارت‌های عجیب، برای مشتری خیالی یک پیشنهاد خلاقانه بسازید!",
                1,
                8,
                45,
                3,
                6,
                75,
                1,
            ),
            (
                "quiz",
                "دانای خانواده",
                "از طبیعت تا فرهنگ ایران؛ ببینید چه کسی بیشتر می‌داند.",
                1,
                6,
                24,
                2,
                6,
                24,
                3,
            ),
            (
                "words",
                "کلمه‌بازی",
                "از سرنخ‌ها کمک بگیرید و پیش از دیگران واژه را پیدا کنید.",
                1,
                4,
                27,
                2,
                6,
                26,
                3,
            ),
        ),
    )
    for kind, cards in CARD_BANK.items():
        conn.executemany(
            "INSERT INTO play_cards VALUES (?,?,?,?,0)",
            ((f"{kind}-{i}", kind, label, detail) for i, (label, detail) in enumerate(cards)),
        )
    conn.executemany(
        "INSERT INTO play_questions VALUES (?,?,?,?,?,?,0)",
        (
            (f"quiz-{i}", prompt, group, level, p.dump(options), answer)
            for i, (prompt, group, level, options, answer) in enumerate(QUESTION_BANK)
        ),
    )
    conn.executemany(
        "INSERT INTO play_words VALUES (?,?,?,?,?,0)",
        (
            (f"word-{i}", word, hint, category, p.dump(banned))
            for i, (word, hint, category, banned) in enumerate(WORD_BANK)
        ),
    )
    conn.executemany(
        "INSERT INTO play_rewards VALUES (?,?,?,?,1)",
        (
            ("first", "اولین قدم", "اولین بازی آنلاین با خانواده", "flag"),
            ("champion", "ستارهٔ خانواده", "اولین پیروزی در یک بازی خانوادگی", "trophy"),
            ("mission", "قهرمان مأموریت", "تکمیل اولین مأموریت و دریافت امتیاز آن", "target"),
            ("community", "سازندهٔ شهر", "همکاری برای ساخت شهر کیلوس", "building"),
        ),
    )
    conn.executemany(
        "INSERT INTO play_campaigns VALUES (?,?,?,?,?,?,?)",
        (
            (
                "spring",
                "هم‌قدم با فروش",
                "فرصتی برای رسیدن به هدف فروش و بازی بیشتر کنار خانواده.",
                date(-12),
                date(19),
                1,
                5,
            ),
            (
                "markets",
                "جشن فروش محله",
                "همکاری ویزیتورها برای همراهی با فروشگاه‌های محله.",
                date(-6),
                date(33),
                1,
                8,
            ),
            (
                "past",
                "همراهی پاییز",
                "دور نخست رقابت فروش و فعال‌سازی خانواده‌ها.",
                date(-58),
                date(-16),
                0,
                3,
            ),
        ),
    )
    conn.executemany(
        "INSERT INTO play_competitions VALUES (?,?,?,?,?,?,?,?,?)",
        (
            (
                "town",
                "با هم شهر کیلوس را می‌سازیم!",
                "هر بازی کامل، یک قدم تا ساختن شهر کوچک ما.",
                "community",
                38,
                "community",
                date(-10),
                date(18),
                1,
            ),
            (
                "league",
                "لیگ خانواده‌های پرانرژی",
                "با بازی، مأموریت و نشان‌ها امتیاز رقابت بگیرید.",
                "rank",
                1,
                None,
                date(-5),
                date(14),
                1,
            ),
        ),
    )
    conn.executemany(
        "INSERT INTO play_missions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            (
                "daily",
                "یک بازی، یک خاطره",
                "امروز یک بازی آنلاین را با خانواده تمام کنید.",
                "member",
                "games",
                1,
                20,
                None,
                date(0),
                date(0),
                1,
            ),
            (
                "team",
                "تیمِ همیشه آماده",
                "تا پایان هفته سه بازی را کامل کنید.",
                "member",
                "games",
                3,
                35,
                None,
                date(-2),
                date(5),
                1,
            ),
            (
                "sell",
                "قدم بعدی در فروش",
                "سه فروش تأییدشده در این دوره ثبت کنید.",
                "visitor",
                "sales",
                3,
                25,
                None,
                stamp(-14),
                date(19),
                1,
            ),
            (
                "goal",
                "عبور از خط هدف",
                "در کمپین هم‌قدم با فروش، از هدف نمونه عبور کنید.",
                "visitor",
                "amount",
                60_000_000,
                40,
                "spring",
                date(-12),
                date(19),
                1,
            ),
        ),
    )
    for index, (key, surname, visitor, region, adult, child) in enumerate(PEOPLE):
        family = p.PRIMARY_FAMILY if index == 0 else f"family-{key}"
        visitor_id = f"visitor-{key}"
        adult_id = p.PRIMARY if index == 0 else f"member-{key}-adult"
        child_id = "member-arin" if index == 0 else f"member-{key}-child"
        conn.execute(
            "INSERT INTO play_families VALUES (?,?,?)", (family, f"خانوادهٔ {surname}", moment)
        )
        conn.execute(
            """INSERT INTO play_accounts
            (id,family_id,role,name,avatar,region,monthly_target,created_at)
            VALUES (?,?,'visitor',?,?,?,?,?)""",
            (
                visitor_id,
                family,
                visitor,
                avatars[(index + 2) % len(avatars)],
                region,
                100_000_000 + (index % 3) * 12_000_000,
                moment,
            ),
        )
        people = [
            (adult_id, family, adult, avatars[index % 8], "adult", moment),
            (child_id, family, child, avatars[(index + 4) % 8], "child", moment),
        ]
        if index == 0:
            people.append(("member-ali", family, "علی", "bear", "adult", moment))
        conn.executemany(
            """INSERT INTO play_accounts (id,family_id,role,name,avatar,age,created_at)
            VALUES (?,?,'member',?,?,?,?)""",
            people,
        )
        conn.execute("INSERT INTO play_campaign_members VALUES ('spring',?)", (visitor_id,))
        if index % 2:
            conn.execute("INSERT INTO play_campaign_members VALUES ('markets',?)", (visitor_id,))
        if index >= 5:
            conn.execute("INSERT INTO play_campaign_members VALUES ('past',?)", (visitor_id,))
        amounts = (
            (47_000_000, 31_000_000)
            if not index
            else ((54 - index * 2) * 1_000_000, (35 - index) * 1_000_000)
        )
        for j, amount in enumerate(amounts):
            age = (6 - j * 2) if not index else 1 + (index * 2 + j * 3) % 6
            at = max(moment - age * 86400, p.epoch(month_start))
            code = f"demo-sale-{key}-{j}"
            bonus = 5 if index and j else 0
            reward = amount // 1_000_000 * 2 + bonus
            conn.execute(
                """INSERT INTO play_sales
                (id,request_id,visitor_id,amount,note,sold_on,created_at,approved_at,
                 approved_by,rule_version,token_amount,campaign_id,campaign_bonus)
                VALUES (?,?,?,?,?,?,?,?,?,1,?,?,?)""",
                (
                    code,
                    p.uid(),
                    visitor_id,
                    amount,
                    ("فروشگاه سپیدار", "فروشگاه بهار")[j],
                    stamp(-age),
                    at,
                    min(moment, at + 3600),
                    p.ADMIN,
                    reward,
                    "spring" if bonus else None,
                    bonus,
                ),
            )
            p.wallet_event(
                conn,
                family,
                "sale",
                code,
                reward,
                "تأیید فروش ثبت‌شده",
                p.ADMIN,
                min(moment, at + 3600),
            )
        sequence = (
            ("shir", "quiz", "words", "quiz", "words")
            if not index
            else (("quiz", "words", "shir") if index in (1, 2, 4) else ("quiz", "words"))
        )
        for j, game in enumerate(sequence):
            at = moment - j * 3_600 - ((index + j * 2) % 6 * 86400 if index else 0)
            score = max(5, (32 if index <= 2 else 28) + (index % 4) * 2 - j * 2)
            cost = {"shir": 8, "quiz": 6, "words": 4}[game]
            code = f"demo-game-{key}-{j}"
            players = [
                (adult_id, adult, avatars[index % 8], score),
                (child_id, child, avatars[(index + 4) % 8], score - 8),
            ]
            if index == 0 and j == 0:
                players.append(("member-ali", "علی", "bear", score - 16))
            # The seed uses historical room-entry tariff per family, not current per-player cost.
            p.wallet_event(conn, family, "entry", code, -cost, "ورود به بازی نمایشی", adult_id, at)
            details = {
                "scores": [dict(id=a, name=n, avatar=v, score=s) for a, n, v, s in players],
                "winners": [adult_id],
                "mode": "guess" if game == "words" else None,
            }
            conn.execute(
                "INSERT INTO play_results VALUES (?,NULL,?,?,1,?,?)",
                (code, family, game, p.dump(details), at),
            )
            for account, _, _, score in players:
                p.add_score(conn, account, family, "game", code, score, at)
                p.grant_badge(conn, account, "first", at=at)
            p.grant_badge(conn, adult_id, "champion", at=at)
    conn.execute(
        """INSERT INTO play_sales (id,request_id,visitor_id,amount,note,sold_on,created_at)
        VALUES ('pending-ali',?,?,22000000,'فروشگاه سپیدار — تکمیل هدف ماهانه',?,?)""",
        (p.uid(), p.VISITOR, stamp(0), moment),
    )
    p.notify(conn, p.PRIMARY, "به باشگاه خانواده خوش آمدید!", "با خانواده‌تان یک اتاق بازی بسازید.")
    p.audit(conn, p.ADMIN, "seed", "دادهٔ اولیهٔ نمایشی آماده شد.", moment)
    p.audit(conn, p.ADMIN, "sales", "فروش اولیهٔ علی رضایی در انتظار تأیید است.", moment)
