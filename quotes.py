"""Curated mindful & contemplative quotes (75 across 5 teachers) + 12 cute Zen E-Ink companions."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Quote:
    text: str
    author: str
    source: str = ""


@dataclass(frozen=True)
class ZenBuddy:
    key: str
    emoji: str
    kaomoji: str
    label: str


AUTHORS: tuple[str, ...] = (
    "Alan Watts",
    "Thích Nhất Hạnh",
    "Ram Dass",
    "Pema Chödrön",
    "Jon Kabat-Zinn",
)

QUOTES: tuple[Quote, ...] = (
    # --- Alan Watts (15) ---
    Quote(
        "Muddy water is best cleared by leaving it alone.",
        "Alan Watts",
        "The Way of Zen",
    ),
    Quote(
        "This is the real secret of life—to be completely engaged with what you are doing in the here and now. And instead of calling it work, realize it is play.",
        "Alan Watts",
        "The Essence of Alan Watts",
    ),
    Quote(
        "The only way to make sense out of change is to plunge into it, move with it, and join the dance.",
        "Alan Watts",
        "The Wisdom of Insecurity",
    ),
    Quote(
        "You are an aperture through which the universe is looking at and exploring itself.",
        "Alan Watts",
        "Eastern Wisdom, Modern Life",
    ),
    Quote(
        "To have faith is to trust yourself to the water. When you swim you don’t grab hold of the water, because if you do you will sink and drown. Instead you relax, and float.",
        "Alan Watts",
        "The Wisdom of Insecurity",
    ),
    Quote(
        "The meaning of life is just to be alive. It is so plain and so obvious and so simple. And yet, everybody rushes around in a great panic as if it were necessary to achieve something beyond themselves.",
        "Alan Watts",
        "The Culture of Counter-Culture",
    ),
    Quote(
        "No valid plans for the future can be made by those who have no capacity for living now.",
        "Alan Watts",
        "The Wisdom of Insecurity",
    ),
    Quote(
        "Try to imagine what it will be like to go to sleep and never wake up… now try to imagine what it was like to wake up having never gone to sleep.",
        "Alan Watts",
        "What Is Reality?",
    ),
    Quote(
        "Listen to your life. See it for the fathomless mystery it is. In the boredom and pain of it, no less than in the excitement and gladness.",
        "Alan Watts",
        "Collected Talks",
    ),
    Quote(
        "You didn’t come into this world. You came out of it, like a wave from the ocean. You are not a stranger here.",
        "Alan Watts",
        "Out of Your Mind",
    ),
    Quote(
        "Man suffers only because he takes seriously what the gods made for fun.",
        "Alan Watts",
        "Alan Watts Journal",
    ),
    Quote(
        "We seldom realize, for example, that our most private thoughts and emotions are not actually our own. For we think in terms of languages and images which we did not invent.",
        "Alan Watts",
        "The Wisdom of Insecurity",
    ),
    Quote(
        "A scholar tries to learn something everyday; a student of Buddhism tries to unlearn something daily.",
        "Alan Watts",
        "The Way of Zen",
    ),
    Quote(
        "Things are as they are. Looking out into the universe at night, we make no comparisons between right and wrong stars, nor between well and badly arranged constellations.",
        "Alan Watts",
        "The Way of Zen",
    ),
    Quote(
        "Tomorrow and plans for tomorrow can have no significance at all unless you are in full contact with the reality of the present, since it is in the present and only in the present that you live.",
        "Alan Watts",
        "The Wisdom of Insecurity",
    ),

    # --- Thích Nhất Hạnh (15) ---
    Quote(
        "Smile, breathe, and go slowly.",
        "Thích Nhất Hạnh",
        "Being Peace",
    ),
    Quote(
        "Feelings come and go like clouds in a windy sky. Conscious breathing is my anchor.",
        "Thích Nhất Hạnh",
        "Stepping into Freedom",
    ),
    Quote(
        "Drink your tea slowly and reverently, as if it is the axis on which the world earth revolves—slowly, evenly, without rushing toward the future.",
        "Thích Nhất Hạnh",
        "The Miracle of Mindfulness",
    ),
    Quote(
        "Peace is present right here and now, in ourselves and in everything we do and see. Every breath we take, every step we take, can be filled with peace, joy, and serenity.",
        "Thích Nhất Hạnh",
        "Peace Is Every Step",
    ),
    Quote(
        "Walk as if you are kissing the Earth with your feet.",
        "Thích Nhất Hạnh",
        "Peace Is Every Step",
    ),
    Quote(
        "No mud, no lotus.",
        "Thích Nhất Hạnh",
        "No Mud, No Lotus",
    ),
    Quote(
        "The present moment is filled with joy and happiness. If you are attentive, you will see it.",
        "Thích Nhất Hạnh",
        "Peace Is Every Step",
    ),
    Quote(
        "Breathing in, I calm body and mind. Breathing out, I smile. Dwelling in the present moment, I know this is the only moment.",
        "Thích Nhất Hạnh",
        "Being Peace",
    ),
    Quote(
        "Thanks to impermanence, everything is possible.",
        "Thích Nhất Hạnh",
        "Going Home",
    ),
    Quote(
        "Sometimes your joy is the source of your smile, but sometimes your smile can be the source of your joy.",
        "Thích Nhất Hạnh",
        "Peace Is Every Step",
    ),
    Quote(
        "Because you are alive, everything is possible.",
        "Thích Nhất Hạnh",
        "Living Buddha, Living Christ",
    ),
    Quote(
        "When another person makes you suffer, it is because he suffers deeply within himself, and his suffering is spilling over. He does not need punishment; he needs help.",
        "Thích Nhất Hạnh",
        "The Heart of Understanding",
    ),
    Quote(
        "Waking up this morning, I smile. Twenty-four brand new hours are before me. I vow to live fully in each moment and to look at all beings with eyes of compassion.",
        "Thích Nhất Hạnh",
        "Peace Is Every Step",
    ),
    Quote(
        "People usually consider walking on water or in thin air a miracle. But I think the real miracle is not to walk either on water or in thin air, but to walk on earth.",
        "Thích Nhất Hạnh",
        "The Miracle of Mindfulness",
    ),
    Quote(
        "There is no way to happiness—happiness is the way.",
        "Thích Nhất Hạnh",
        "The Art of Power",
    ),

    # --- Ram Dass (15) ---
    Quote(
        "Be here now.",
        "Ram Dass",
        "Be Here Now",
    ),
    Quote(
        "We’re all just walking each other home.",
        "Ram Dass",
        "Sit Around the Fire",
    ),
    Quote(
        "The quieter you become, the more you can hear.",
        "Ram Dass",
        "Be Here Now",
    ),
    Quote(
        "Treat everyone you meet like God in drag.",
        "Ram Dass",
        "Polishing the Mirror",
    ),
    Quote(
        "Don’t try to control the wind; simply adjust your sails and witness the ride with an open heart.",
        "Ram Dass",
        "Talks on Awareness",
    ),
    Quote(
        "Unconditional love really exists in each of us. It is part of our deep inner being. It is not so much an active emotion as a state of being.",
        "Ram Dass",
        "Compassion in Action",
    ),
    Quote(
        "Think of yourself as a cloud. Clouds never make mistakes. Did you ever see a cloud that was misshapen?",
        "Ram Dass",
        "Be Here Now",
    ),
    Quote(
        "When the mind is quiet, the sun of your own heart shines gently on everything.",
        "Ram Dass",
        "Polishing the Mirror",
    ),
    Quote(
        "Everything changes once we identify with being the witness to the story, instead of the actor in it.",
        "Ram Dass",
        "Still Here",
    ),
    Quote(
        "I would like my life to be a statement of love and compassion—and where it isn’t, that’s where my work lies.",
        "Ram Dass",
        "Be Love Now",
    ),
    Quote(
        "A tree doesn’t judge another tree for growing gnarled. Trees simply stand together in the forest and turn toward the light.",
        "Ram Dass",
        "Experiments in Truth",
    ),
    Quote(
        "Suffering is part of our training program for becoming wise.",
        "Ram Dass",
        "Still Here",
    ),
    Quote(
        "The game is not about becoming somebody; it’s about becoming nobody.",
        "Ram Dass",
        "Grist for the Mill",
    ),
    Quote(
        "The next message you need is always right where you are.",
        "Ram Dass",
        "Be Here Now",
    ),
    Quote(
        "Your problem is you’re too busy holding on to your unworthiness.",
        "Ram Dass",
        "Polishing the Mirror",
    ),

    # --- Pema Chödrön (15) ---
    Quote(
        "You are the sky. Everything else—it’s just the weather.",
        "Pema Chödrön",
        "Start Where You Are",
    ),
    Quote(
        "Nothing ever goes away until it has taught us what we need to know.",
        "Pema Chödrön",
        "When Things Fall Apart",
    ),
    Quote(
        "Start where you are. This is very important. Meditation practice is not about later, when you get it all together.",
        "Pema Chödrön",
        "Start Where You Are",
    ),
    Quote(
        "To be fully alive, fully human, and completely awake is to be continually thrown out of the nest.",
        "Pema Chödrön",
        "When Things Fall Apart",
    ),
    Quote(
        "Compassion is not a relationship between the healer and the wounded. It’s a relationship between equals.",
        "Pema Chödrön",
        "The Places That Scare You",
    ),
    Quote(
        "Fear is a natural reaction to moving closer to the truth.",
        "Pema Chödrön",
        "When Things Fall Apart",
    ),
    Quote(
        "Letting there be room for not knowing is the most important thing of all.",
        "Pema Chödrön",
        "When Things Fall Apart",
    ),
    Quote(
        "Gentleness with ourselves is the foundation of fearlessness.",
        "Pema Chödrön",
        "The Wisdom of No Escape",
    ),
    Quote(
        "Every day, think as you wake up: today I am fortunate to be alive, I have a precious human life, I am not going to waste it.",
        "Pema Chödrön",
        "The Places That Scare You",
    ),
    Quote(
        "The most fundamental aggression to ourselves, the most fundamental harm we can do to ourselves, is to remain ignorant by not having the courage and the respect to look at ourselves honestly and gently.",
        "Pema Chödrön",
        "When Things Fall Apart",
    ),
    Quote(
        "Only to the extent that we expose ourselves over and over to annihilation can that which is indestructible in us be found.",
        "Pema Chödrön",
        "When Things Fall Apart",
    ),
    Quote(
        "Curiosity and tenderness are the twin antidotes to tightness of heart.",
        "Pema Chödrön",
        "Living Beautifully",
    ),
    Quote(
        "If we learn to open our hearts, anyone, including the people who drive us crazy, can be our teacher.",
        "Pema Chödrön",
        "Start Where You Are",
    ),
    Quote(
        "Healing comes from letting there be room for all of this to happen: room for grief, for relief, for misery, for joy.",
        "Pema Chödrön",
        "When Things Fall Apart",
    ),
    Quote(
        "Stay with the shakiness—stay with the broken heart and the soft spot.",
        "Pema Chödrön",
        "The Places That Scare You",
    ),

    # --- Jon Kabat-Zinn (15) ---
    Quote(
        "You can’t stop the waves, but you can learn to surf.",
        "Jon Kabat-Zinn",
        "Wherever You Go, There You Are",
    ),
    Quote(
        "Wherever you go, there you are.",
        "Jon Kabat-Zinn",
        "Wherever You Go, There You Are",
    ),
    Quote(
        "The little things? The little moments? They aren’t little.",
        "Jon Kabat-Zinn",
        "Mindfulness for Beginners",
    ),
    Quote(
        "Mindfulness means paying attention in a particular way: on purpose, in the present moment, and nonjudgmentally.",
        "Jon Kabat-Zinn",
        "Wherever You Go, There You Are",
    ),
    Quote(
        "As long as you are breathing, there is more right with you than wrong with you, no matter what is wrong.",
        "Jon Kabat-Zinn",
        "Full Catastrophe Living",
    ),
    Quote(
        "Patience is a form of wisdom. It demonstrates that we understand and accept the fact that sometimes things must unfold in their own time.",
        "Jon Kabat-Zinn",
        "Wherever You Go, There You Are",
    ),
    Quote(
        "Notice that in this very moment, nothing needs to be fixed for you to simply rest in awareness.",
        "Jon Kabat-Zinn",
        "Coming to Our Senses",
    ),
    Quote(
        "Your breathing is your greatest friend. Return to it in all your troubles and you will find comfort and guidance.",
        "Jon Kabat-Zinn",
        "Wherever You Go, There You Are",
    ),
    Quote(
        "Drop out of the stream of doing for a moment, and simply allow yourself to be.",
        "Jon Kabat-Zinn",
        "Wherever You Go, There You Are",
    ),
    Quote(
        "Awareness is a spacious vessel—big enough to hold whatever arises without needing to push any of it away.",
        "Jon Kabat-Zinn",
        "Falling Awake",
    ),
    Quote(
        "The best way to capture moments is to pay attention. This is how we cultivate mindfulness.",
        "Jon Kabat-Zinn",
        "Wherever You Go, There You Are",
    ),
    Quote(
        "Each morning is a quiet invitation to begin again, right from this breath.",
        "Jon Kabat-Zinn",
        "Mindfulness for Beginners",
    ),
    Quote(
        "When you pay attention to boredom, it gets unbelievably interesting.",
        "Jon Kabat-Zinn",
        "Wherever You Go, There You Are",
    ),
    Quote(
        "Real meditation practice is how we live our lives from moment to moment to moment.",
        "Jon Kabat-Zinn",
        "Wherever You Go, There You Are",
    ),
    Quote(
        "Give yourself permission to allow this moment to be exactly as it is, and allow yourself to be exactly as you are.",
        "Jon Kabat-Zinn",
        "Wherever You Go, There You Are",
    ),
)

ZEN_BUDDIES: tuple[ZenBuddy, ...] = (
    ZenBuddy("capybara", "🍊", "( ˘ ᴥ ˘ )", "yuzu capybara"),
    ZenBuddy("teacup", "🍵", "(˘▽˘)っ♨", "warm matcha"),
    ZenBuddy("kitty", "🐱", "(=^･ω･^=)", "zen kitty"),
    ZenBuddy("lotus", "🪷", "(✿ ◠‿◠)", "lotus bloom"),
    ZenBuddy("frog", "🐸", "( • ‿ • )✧", "pond friend"),
    ZenBuddy("turtle", "🐢", "(๑•ᴗ•๑)♡", "go slowly"),
    ZenBuddy("bonsai", "🪴", "(◕‿◕) ❀", "little bonsai"),
    ZenBuddy("boba", "🧋", "( ˘▾˘ )っ", "happy boba"),
    ZenBuddy("shiba", "🐕", "( ᵔ ᴥ ᵔ )", "sunny pup"),
    ZenBuddy("cloud", "☁️", "( ˘ ³˘) ☁", "soft cloud"),
    ZenBuddy("sprout", "🌱", "(◕‿◕) ✿", "happy sprout"),
    ZenBuddy("moon", "🌙", "( ˘ω˘ ) zZ", "cozy spirit"),
)

BUDDY_BY_KEY: dict[str, ZenBuddy] = {b.key: b for b in ZEN_BUDDIES}


def select_quote_and_buddy(
    rotate_minutes: int = 60,
    offset: int = 0,
    author_filter: str = "all",
    buddy_mode: str = "auto",
    now_ts: float | None = None,
) -> tuple[Quote, ZenBuddy]:
    """Deterministically pick a quote + cute Zen buddy for the current time bucket."""
    ts = now_ts if now_ts is not None else time.time()
    bucket = int(ts // max(60, rotate_minutes * 60)) + offset
    digest = hashlib.sha256(f"kindle-zen-{bucket}-{author_filter}".encode()).digest()

    if author_filter and author_filter.lower() != "all":
        pool = tuple(q for q in QUOTES if q.author.lower() == author_filter.lower())
        if not pool:
            pool = QUOTES
    else:
        pool = QUOTES

    q_idx = int.from_bytes(digest[:4], "big") % len(pool)

    if buddy_mode and buddy_mode != "auto" and buddy_mode in BUDDY_BY_KEY:
        buddy = BUDDY_BY_KEY[buddy_mode]
    else:
        b_idx = int.from_bytes(digest[4:8], "big") % len(ZEN_BUDDIES)
        buddy = ZEN_BUDDIES[b_idx]

    return pool[q_idx], buddy
