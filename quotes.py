"""Curated mindful & contemplative quotes (320+ across 9 teachers) + 12 cute Zen E-Ink companions.

Uses OS-entropy Fisher-Yates shuffled decks (persisted to disk) with author de-clumping and
cross-deck boundary protection so every screen update shows a fresh quote without repeats.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SYS_RNG = secrets.SystemRandom()


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
    "Shunryu Suzuki",
    "Lao Tzu",
    "Jack Kornfield",
    "Tara Brach",
)

QUOTES: tuple[Quote, ...] = (
    # --- Alan Watts (40) ---
    Quote("Muddy water is best cleared by leaving it alone.", "Alan Watts", "The Way of Zen"),
    Quote("This is the real secret of life—to be completely engaged with what you are doing in the here and now. And instead of calling it work, realize it is play.", "Alan Watts", "The Essence of Alan Watts"),
    Quote("The only way to make sense out of change is to plunge into it, move with it, and join the dance.", "Alan Watts", "The Wisdom of Insecurity"),
    Quote("You are an aperture through which the universe is looking at and exploring itself.", "Alan Watts", "Eastern Wisdom, Modern Life"),
    Quote("To have faith is to trust yourself to the water. When you swim you don’t grab hold of the water, because if you do you will sink. Instead you relax, and float.", "Alan Watts", "The Wisdom of Insecurity"),
    Quote("No valid plans for the future can be made by those who have no capacity for living now.", "Alan Watts", "The Wisdom of Insecurity"),
    Quote("Try to imagine what it will be like to go to sleep and never wake up… now try to imagine what it was like to wake up having never gone to sleep.", "Alan Watts", "What Is Reality?"),
    Quote("Listen to your life. See it for the fathomless mystery it is. In the boredom and pain of it, no less than in the excitement and gladness.", "Alan Watts", "Collected Talks"),
    Quote("You didn’t come into this world. You came out of it, like a wave from the ocean. You are not a stranger here.", "Alan Watts", "Out of Your Mind"),
    Quote("Man suffers only because he takes seriously what the gods made for fun.", "Alan Watts", "Alan Watts Journal"),
    Quote("We seldom realize that our most private thoughts and emotions are not actually our own. For we think in terms of languages and images which we did not invent.", "Alan Watts", "The Wisdom of Insecurity"),
    Quote("A scholar tries to learn something every day; a student of Buddhism tries to unlearn something daily.", "Alan Watts", "The Way of Zen"),
    Quote("Things are as they are. Looking out into the universe at night, we make no comparisons between right and wrong stars, nor between well and badly arranged constellations.", "Alan Watts", "The Way of Zen"),
    Quote("You are under no obligation to be the same person you were five minutes ago.", "Alan Watts", "Collected Talks"),
    Quote("The art of living is neither careless drifting on the one hand nor fearful clinging to the past on the other.", "Alan Watts", "The Wisdom of Insecurity"),
    Quote("Life is not a journey to a destination; it is a musical thing, and you are supposed to sing or dance while the music is being played.", "Alan Watts", "Out of Your Mind"),
    Quote("Through our eyes, the universe is perceiving itself. Through our ears, the universe is listening to its harmonies.", "Alan Watts", "The Book"),
    Quote("What you do is what the whole universe is doing at the place you call here and now.", "Alan Watts", "The Book"),
    Quote("Stop measuring days by degree of productivity and start experiencing them by degree of presence.", "Alan Watts", "Lectures on Zen"),
    Quote("Zen does not confuse spirituality with thinking about God while one is peeling potatoes. Zen spirituality is just to peel the potatoes.", "Alan Watts", "The Way of Zen"),
    Quote("The desire for security and the feeling of insecurity are the same thing. To hold your breath is to lose your breath.", "Alan Watts", "The Wisdom of Insecurity"),
    Quote("Just as true humor is laughter at oneself, true humanity is knowledge of oneself.", "Alan Watts", "The Wisdom of Insecurity"),
    Quote("Never pretend to a love which you do not actually feel, for love is not ours to command.", "Alan Watts", "The Wisdom of Insecurity"),
    Quote("When we attempt to exercise power or control over someone else, we cannot avoid giving that person the very same power over us.", "Alan Watts", "The Way of Zen"),
    Quote("To remain stable is to refrain from trying to separate yourself from a pain because you know that you cannot.", "Alan Watts", "The Wisdom of Insecurity"),
    Quote("Reality is only a Rorschach ink-blot, you know.", "Alan Watts", "The Taboo Against Knowing Who You Are"),
    Quote("Hurry and postponement are twin ways of avoiding the present.", "Alan Watts", "Cloud-Hidden, Whereabouts Unknown"),
    Quote("When there is no longer any desire to be undisturbed, disturbance itself vanishes.", "Alan Watts", "The Way of Zen"),
    Quote("Every individual is an expression of the whole realm of nature, a unique action of the total universe.", "Alan Watts", "The Book"),
    Quote("The menu is not the meal; the map is not the territory.", "Alan Watts", "The Way of Zen"),
    Quote("What we have forgotten is that thoughts and words are conventions, and that it is fatal to take conventions too seriously.", "Alan Watts", "The Way of Zen"),
    Quote("In music, one doesn’t make the end of the composition the point of the composition. If that were so, the best conductors would be those who played fastest.", "Alan Watts", "The Essence of Alan Watts"),
    Quote("Without birth and death, and without the perpetual transmutation of all the forms of life, the world would be static, rhythm-less, undancing, mummified.", "Alan Watts", "The Wisdom of Insecurity"),
    Quote("You and I are all as much continuous with the physical universe as a wave is continuous with the ocean.", "Alan Watts", "Out of Your Mind"),
    Quote("Problems that remain persistently insoluble should always be suspected as questions asked in the wrong way.", "Alan Watts", "The Book"),
    Quote("Life is a dance, and when you are dancing you are not intent on getting somewhere—the meaning is in the movement itself.", "Alan Watts", "The Wisdom of Insecurity"),
    Quote("A cloud never hurries, yet every drop of rain arrives right on time.", "Alan Watts", "Cloud-Hidden, Whereabouts Unknown"),
    Quote("Nothing is more creative than emptiness—space in which anything may appear and pass away without leaving a scratch.", "Alan Watts", "The Way of Zen"),
    Quote("Sitting quietly, doing nothing, spring comes, and the grass grows by itself.", "Alan Watts", "The Way of Zen"),
    Quote("Waking up to who you are requires letting go of who you imagine yourself to be.", "Alan Watts", "The Book"),

    # --- Thích Nhất Hạnh (40) ---
    Quote("Smile, breathe, and go slowly.", "Thích Nhất Hạnh", "Being Peace"),
    Quote("Feelings come and go like clouds in a windy sky. Conscious breathing is my anchor.", "Thích Nhất Hạnh", "Stepping into Freedom"),
    Quote("Drink your tea slowly and reverently, as if it is the axis on which the world earth revolves—slowly, evenly, without rushing toward the future.", "Thích Nhất Hạnh", "The Miracle of Mindfulness"),
    Quote("Peace is present right here and now, in ourselves and in everything we do and see.", "Thích Nhất Hạnh", "Peace Is Every Step"),
    Quote("Walk as if you are kissing the Earth with your feet.", "Thích Nhất Hạnh", "Peace Is Every Step"),
    Quote("No mud, no lotus.", "Thích Nhất Hạnh", "No Mud, No Lotus"),
    Quote("The present moment is filled with joy and happiness. If you are attentive, you will see it.", "Thích Nhất Hạnh", "Peace Is Every Step"),
    Quote("Breathing in, I calm body and mind. Breathing out, I smile. Dwelling in the present moment, I know this is the only moment.", "Thích Nhất Hạnh", "Being Peace"),
    Quote("Thanks to impermanence, everything is possible.", "Thích Nhất Hạnh", "Going Home"),
    Quote("Sometimes your joy is the source of your smile, but sometimes your smile can be the source of your joy.", "Thích Nhất Hạnh", "Peace Is Every Step"),
    Quote("Because you are alive, everything is possible.", "Thích Nhất Hạnh", "Living Buddha, Living Christ"),
    Quote("When another person makes you suffer, it is because he suffers deeply within himself, and his suffering is spilling over. He needs help.", "Thích Nhất Hạnh", "The Heart of Understanding"),
    Quote("Waking up this morning, I smile. Twenty-four brand new hours are before me. I vow to live fully in each moment.", "Thích Nhất Hạnh", "Peace Is Every Step"),
    Quote("People usually consider walking on water a miracle. But I think the real miracle is not to walk on water, but to walk peacefully on earth.", "Thích Nhất Hạnh", "The Miracle of Mindfulness"),
    Quote("There is no way to happiness—happiness is the way.", "Thích Nhất Hạnh", "The Art of Power"),
    Quote("To be beautiful means to be yourself. You don’t need to be accepted by others. You need to accept yourself.", "Thích Nhất Hạnh", "The Art of Communicating"),
    Quote("Life is available only in the present moment. If you abandon the present moment, you cannot live the moments of your daily life deeply.", "Thích Nhất Hạnh", "You Are Here"),
    Quote("Deep listening is the kind of listening that can help relieve the suffering of another person.", "Thích Nhất Hạnh", "The Art of Communicating"),
    Quote("Understanding is love’s other name. If you don’t understand, you can’t love.", "Thích Nhất Hạnh", "How to Love"),
    Quote("Letting go gives us freedom, and freedom is the only condition for happiness.", "Thích Nhất Hạnh", "The Heart of the Buddha’s Teaching"),
    Quote("Every breath we take, every step we make, can be filled with peace, joy, and serenity.", "Thích Nhất Hạnh", "Peace Is Every Step"),
    Quote("A cloud never dies. It becomes rain, snow, mist, and then a cup of warm tea in your hands.", "Thích Nhất Hạnh", "No Death, No Fear"),
    Quote("If you love someone, the greatest gift you can offer them is your true presence.", "Thích Nhất Hạnh", "True Love"),
    Quote("Washing the dishes to wash the dishes—not in order to hurry to the next thing—is already enlightenment.", "Thích Nhất Hạnh", "The Miracle of Mindfulness"),
    Quote("Anger is like a crying baby. Hold it tenderly in mindfulness until it calms down.", "Thích Nhất Hạnh", "Anger"),
    Quote("Silence is essential. We need silence, just as much as we need air, just as much as plants need light.", "Thích Nhất Hạnh", "Silence"),
    Quote("When a lettuce does not grow well, we do not blame the lettuce. We look for reasons—more sun, water, or care.", "Thích Nhất Hạnh", "Peace Is Every Step"),
    Quote("Hope is important, yet peace begins the moment we return fully to what is already here.", "Thích Nhất Hạnh", "Peace Is Every Step"),
    Quote("Enlightenment is when a wave realizes it is the ocean.", "Thích Nhất Hạnh", "The Sun My Heart"),
    Quote("Freedom is not given to us by anyone; we have to cultivate it ourselves, step by mindful step.", "Thích Nhất Hạnh", "How to Walk"),
    Quote("Do not lose yourself in the past. Do not lose yourself in the future. Come back to the present breath.", "Thích Nhất Hạnh", "Our Appointment with Life"),
    Quote("Mindfulness is the energy that helps us recognize the conditions of happiness that are already present in our lives.", "Thích Nhất Hạnh", "Fear"),
    Quote("Your true home is not an abstract place in the future; your true home is the here and the now.", "Thích Nhất Hạnh", "You Are Here"),
    Quote("Speak truthfully and gently, using words that inspire confidence, harmony, and relief.", "Thích Nhất Hạnh", "Being Peace"),
    Quote("A single quiet breath can interrupt a thousand miles of rushing.", "Thích Nhất Hạnh", "How to Sit"),
    Quote("In a crowded room, one calm person is like a cool shade tree—everyone benefits simply from their stillness.", "Thích Nhất Hạnh", "Being Peace"),
    Quote("Look deeply at a flower and you can see clouds, sunshine, soil, and patience woven together.", "Thích Nhất Hạnh", "The Heart of Understanding"),
    Quote("Rest is a precondition for healing. Allow your body to rest the way a pebble rests at the bottom of a clear stream.", "Thích Nhất Hạnh", "How to Relax"),
    Quote("Even in the middle of difficulty, the blue sky above the clouds has never gone anywhere.", "Thích Nhất Hạnh", "Peace Is Every Step"),
    Quote("We have more possibilities available in each moment than we realize.", "Thích Nhất Hạnh", "Peace Is Every Step"),

    # --- Ram Dass (40) ---
    Quote("Be here now.", "Ram Dass", "Be Here Now"),
    Quote("We’re all just walking each other home.", "Ram Dass", "Sit Around the Fire"),
    Quote("The quieter you become, the more you can hear.", "Ram Dass", "Be Here Now"),
    Quote("Treat everyone you meet like God in drag.", "Ram Dass", "Polishing the Mirror"),
    Quote("Don’t try to control the wind; simply adjust your sails and witness the ride with an open heart.", "Ram Dass", "Talks on Awareness"),
    Quote("Unconditional love really exists in each of us. It is part of our deep inner being—not so much an emotion as a state of being.", "Ram Dass", "Compassion in Action"),
    Quote("Think of yourself as a cloud. Clouds never make mistakes. Did you ever see a cloud that was misshapen?", "Ram Dass", "Be Here Now"),
    Quote("When the mind is quiet, the sun of your own heart shines gently on everything.", "Ram Dass", "Polishing the Mirror"),
    Quote("Everything changes once we identify with being the witness to the story, instead of the actor in it.", "Ram Dass", "Still Here"),
    Quote("I would like my life to be a statement of love and compassion—and where it isn’t, that’s where my work lies.", "Ram Dass", "Be Love Now"),
    Quote("A tree doesn’t judge another tree for growing gnarled. Trees simply stand together in the forest and turn toward the light.", "Ram Dass", "Experiments in Truth"),
    Quote("Suffering is part of our training program for becoming wise.", "Ram Dass", "Still Here"),
    Quote("The game is not about becoming somebody; it’s about becoming nobody.", "Ram Dass", "Grist for the Mill"),
    Quote("The next message you need is always right where you are.", "Ram Dass", "Be Here Now"),
    Quote("Your problem is you’re too busy holding on to your unworthiness.", "Ram Dass", "Polishing the Mirror"),
    Quote("Healing does not mean going back to the way things were before, but rather allowing what is now to move us closer to openness.", "Ram Dass", "Still Here"),
    Quote("Heartbreak is just the ego’s shell cracking open so a larger love can breathe.", "Ram Dass", "Polishing the Mirror"),
    Quote("It is important to expect nothing, to take every experience, including the negative ones, as merely steps on the path.", "Ram Dass", "Be Here Now"),
    Quote("As long as you have certain desires about how it ought to be, you can’t see how it is.", "Ram Dass", "Grist for the Mill"),
    Quote("Compassion refers to the arising in the heart of the desire to relieve the suffering of all beings.", "Ram Dass", "Compassion in Action"),
    Quote("You can do it like it’s a great weight on you, or you can do it like it’s part of the dance.", "Ram Dass", "Be Here Now"),
    Quote("In most relationships we spend much of our time reassuring one another that our costumes of identity are still on straight.", "Ram Dass", "Journey of Awakening"),
    Quote("If you think you’re enlightened, go spend a week with your family.", "Ram Dass", "Be Here Now"),
    Quote("Faith is in the heart, while beliefs are in the head.", "Ram Dass", "Polishing the Mirror"),
    Quote("Our journey is about being more deeply involved in life, and yet less attached to it.", "Ram Dass", "Be Here Now"),
    Quote("Notice how much lighter life feels the moment you stop rehearsing tomorrow’s arguments.", "Ram Dass", "Walking Each Other Home"),
    Quote("You are loved just for being who you are, just for existing. You don’t have to do anything to earn it.", "Ram Dass", "Be Love Now"),
    Quote("Grace is everywhere once we stop insisting it arrive in the package we ordered.", "Ram Dass", "Still Here"),
    Quote("Whenever you catch yourself contracting in judgment, soften and say inwardly: ah, another human being just like me.", "Ram Dass", "Polishing the Mirror"),
    Quote("Stillness is not the absence of motion; it is the spacious heart watching motion come and go.", "Ram Dass", "Journey of Awakening"),
    Quote("We are all affecting the world every moment, whether we mean to or not. Our quietest state of mind radiates outward.", "Ram Dass", "Compassion in Action"),
    Quote("Everything in your life is there as a vehicle for your transformation. Use it!", "Ram Dass", "Grist for the Mill"),
    Quote("When you know how to listen, everybody is the guru.", "Ram Dass", "Be Here Now"),
    Quote("Let your busy mind drop down into the warm, steady cave of the heart.", "Ram Dass", "Polishing the Mirror"),
    Quote("We’re fascinated by the words, but where we truly meet is in the silence behind them.", "Ram Dass", "Be Here Now"),
    Quote("Aging and change are only frightening to the part of us that clings; to awareness itself, nothing is lost.", "Ram Dass", "Still Here"),
    Quote("Honor your humanity—the stumbles, the tenderness, the humor—without turning it into a courtroom.", "Ram Dass", "Be Love Now"),
    Quote("Joy is what remains naturally when we stop demanding that this moment be different.", "Ram Dass", "Polishing the Mirror"),
    Quote("One candle doesn’t lose any of its flame by lighting another.", "Ram Dass", "Compassion in Action"),
    Quote("Rest in the witness: thoughts pass across the screen, and the screen itself stays clear.", "Ram Dass", "Journey of Awakening"),

    # --- Pema Chödrön (40) ---
    Quote("You are the sky. Everything else—it’s just the weather.", "Pema Chödrön", "Start Where You Are"),
    Quote("Nothing ever goes away until it has taught us what we need to know.", "Pema Chödrön", "When Things Fall Apart"),
    Quote("Start where you are. This is very important. Meditation practice is not about later, when you get it all together.", "Pema Chödrön", "Start Where You Are"),
    Quote("To be fully alive, fully human, and completely awake is to be continually thrown out of the nest.", "Pema Chödrön", "When Things Fall Apart"),
    Quote("Compassion is not a relationship between the healer and the wounded. It’s a relationship between equals.", "Pema Chödrön", "The Places That Scare You"),
    Quote("Fear is a natural reaction to moving closer to the truth.", "Pema Chödrön", "When Things Fall Apart"),
    Quote("Letting there be room for not knowing is the most important thing of all.", "Pema Chödrön", "When Things Fall Apart"),
    Quote("Gentleness with ourselves is the foundation of fearlessness.", "Pema Chödrön", "The Wisdom of No Escape"),
    Quote("Every day, think as you wake up: today I am fortunate to be alive, I have a precious human life, I am not going to waste it.", "Pema Chödrön", "The Places That Scare You"),
    Quote("Only to the extent that we expose ourselves over and over to annihilation can that which is indestructible in us be found.", "Pema Chödrön", "When Things Fall Apart"),
    Quote("Curiosity and tenderness are the twin antidotes to tightness of heart.", "Pema Chödrön", "Living Beautifully"),
    Quote("If we learn to open our hearts, anyone, including the people who drive us crazy, can be our teacher.", "Pema Chödrön", "Start Where You Are"),
    Quote("Healing comes from letting there be room for all of this to happen: room for grief, for relief, for misery, for joy.", "Pema Chödrön", "When Things Fall Apart"),
    Quote("Stay with the shakiness—stay with the broken heart and the soft spot.", "Pema Chödrön", "The Places That Scare You"),
    Quote("Rather than letting negativity get the better of us, we can meet our rough edges with honesty, humor, and an open heart.", "Pema Chödrön", "When Things Fall Apart"),
    Quote("We think the point is to pass the test or fix the problem, when the truth is that things come together and things fall apart.", "Pema Chödrön", "When Things Fall Apart"),
    Quote("Drop the storyline and feel the underlying energy right here in your body.", "Pema Chödrön", "Taking the Leap"),
    Quote("When there’s a big disappointment, we don’t know if that’s the end of the story. It may just be the beginning of a great adventure.", "Pema Chödrön", "When Things Fall Apart"),
    Quote("Pause for three conscious breaths before reacting; in that tiny gap lives your freedom.", "Pema Chödrön", "Taking the Leap"),
    Quote("Be kinder to yourself. And then let your kindness flood the world.", "Pema Chödrön", "Welcoming the Unwelcome"),
    Quote("Impermanence is a principle of harmony. When we don’t struggle against it, we are in harmony with reality.", "Pema Chödrön", "When Things Fall Apart"),
    Quote("The most difficult times for many of us are the ones we give ourselves.", "Pema Chödrön", "When Things Fall Apart"),
    Quote("Whatever occurs is fresh, unbound, and workable when met with an unguarded heart.", "Pema Chödrön", "Living Beautifully"),
    Quote("Relaxing with the ambiguity and uncertainty of the present moment is the root of genuine confidence.", "Pema Chödrön", "Comfortable with Uncertainty"),
    Quote("Instead of armoring our hearts, we can let everyday irritations polish us softer and wiser.", "Pema Chödrön", "Start Where You Are"),
    Quote("Meditation is not about trying to achieve ecstasy or bliss; it is about becoming completely honest and friendly with ourselves.", "Pema Chödrön", "The Wisdom of No Escape"),
    Quote("Notice the urge to harden, and see what happens when you breathe right into that tender place instead.", "Pema Chödrön", "The Places That Scare You"),
    Quote("Patience has nothing to do with gritting our teeth; it means opening to the rawness of right now without rushing for the exit.", "Pema Chödrön", "Comfortable with Uncertainty"),
    Quote("Every moment is a crossroads where we can either tighten in habit or soften in awareness.", "Pema Chödrön", "Taking the Leap"),
    Quote("Rejoice in ordinary things—morning light on a wall, cool air on your face, a quiet cup of water.", "Pema Chödrön", "The Wisdom of No Escape"),
    Quote("True bravery is willingness to stay open when we don’t get our way.", "Pema Chödrön", "The Places That Scare You"),
    Quote("You never really lose your basic goodness, any more than the sky loses its openness during a storm.", "Pema Chödrön", "Welcoming the Unwelcome"),
    Quote("Wholeheartedness means bringing warmth even to our own boredom, restlessness, and doubt.", "Pema Chödrön", "Start Where You Are"),
    Quote("To love the world well, begin by making peace with the unruly guest house of your own mind.", "Pema Chödrön", "Living Beautifully"),
    Quote("Let life touch you—even when the touch is bittersweet, it wakes your heart from slumber.", "Pema Chödrön", "How We Live Is How We Die"),
    Quote("Humor is one of our greatest allies; a light touch dissolves decades of solemn self-importance.", "Pema Chödrön", "Start Where You Are"),
    Quote("Each exhale is a natural practice of letting go—nothing forced, nothing held back.", "Pema Chödrön", "The Wisdom of No Escape"),
    Quote("Where we stumble is the exact ground from which we stand up wiser.", "Pema Chödrön", "Fail, Fail Again, Fail Better"),
    Quote("Awakened heart is already present in that first impulse of care for a tired friend or a stray bird.", "Pema Chödrön", "Welcoming the Unwelcome"),
    Quote("Hold your plans lightly, so surprise can still enter the room as a friend.", "Pema Chödrön", "Comfortable with Uncertainty"),

    # --- Jon Kabat-Zinn (40) ---
    Quote("You can’t stop the waves, but you can learn to surf.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Wherever you go, there you are.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("The little things? The little moments? They aren’t little.", "Jon Kabat-Zinn", "Mindfulness for Beginners"),
    Quote("Mindfulness means paying attention in a particular way: on purpose, in the present moment, and nonjudgmentally.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("As long as you are breathing, there is more right with you than wrong with you, no matter what is wrong.", "Jon Kabat-Zinn", "Full Catastrophe Living"),
    Quote("Patience is a form of wisdom. It demonstrates that we understand and accept that sometimes things must unfold in their own time.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Notice that in this very moment, nothing needs to be fixed for you to simply rest in awareness.", "Jon Kabat-Zinn", "Coming to Our Senses"),
    Quote("Your breathing is your greatest friend. Return to it in all your troubles and you will find comfort and guidance.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Drop out of the stream of doing for a moment, and simply allow yourself to be.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Awareness is a spacious vessel—big enough to hold whatever arises without needing to push any of it away.", "Jon Kabat-Zinn", "Falling Awake"),
    Quote("The best way to capture moments is to pay attention. This is how we cultivate mindfulness.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Each morning is a quiet invitation to begin again, right from this breath.", "Jon Kabat-Zinn", "Mindfulness for Beginners"),
    Quote("When you pay attention to boredom, it gets unbelievably interesting.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Real meditation practice is how we live our lives from moment to moment to moment.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Give yourself permission to allow this moment to be exactly as it is, and allow yourself to be exactly as you are.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("We take care of the future best by taking care of the present now.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Non-doing simply means letting things be and allowing them to unfold in their own way.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Your thoughts are weather events in the mind—real while passing through, yet not permanent facts.", "Jon Kabat-Zinn", "Mindfulness for Beginners"),
    Quote("Feel your feet on the floor and your shoulders softening; the body always lives in the present.", "Jon Kabat-Zinn", "Coming to Our Senses"),
    Quote("In stillness, we rediscover a wholeness that busyness only obscured, never destroyed.", "Jon Kabat-Zinn", "Full Catastrophe Living"),
    Quote("Simplicity is choosing to inhabit one moment wholeheartedly instead of ten moments halfheartedly.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Every breath is a new beginning, and every exhale is a complete release.", "Jon Kabat-Zinn", "Falling Awake"),
    Quote("Meditation is the only intentional, systematic human activity which at bottom is about not trying to improve yourself, but realizing where you already are.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("You don’t have to like everything that arises in order to greet it with calm clarity.", "Jon Kabat-Zinn", "Full Catastrophe Living"),
    Quote("Sit like a mountain: rooted as seasons, storms, and sunlight pass across your slopes.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Rest like a clear mountain lake, reflecting sky and trees without clinging to any reflection.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Notice how often the mind races ahead to arrive somewhere, missing the richness of being right here.", "Jon Kabat-Zinn", "Coming to Our Senses"),
    Quote("Kindness toward your own wandering mind is the heart of the entire practice.", "Jon Kabat-Zinn", "Mindfulness for Beginners"),
    Quote("Even ten seconds of sincere presence can reset the tone of an entire afternoon.", "Jon Kabat-Zinn", "Arriving at Your Own Door"),
    Quote("To see clearly, let the sediment of urgency settle on its own.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Listening to birdsong or rain without commentary brings us straight back to our senses.", "Jon Kabat-Zinn", "Coming to Our Senses"),
    Quote("You are bigger than any single mood, task, or worry passing through today.", "Jon Kabat-Zinn", "Full Catastrophe Living"),
    Quote("Trust your own quiet knowing; beneath the noise, an unhurried intelligence is already at work.", "Jon Kabat-Zinn", "Wherever You Go, There You Are"),
    Quote("Beginner’s mind frees us from the tyranny of thinking we already know how this day will feel.", "Jon Kabat-Zinn", "Mindfulness for Beginners"),
    Quote("Acceptance is not passive resignation; it is seeing things clearly as they actually are right now.", "Jon Kabat-Zinn", "Full Catastrophe Living"),
    Quote("Let your attention rest lightly, like a butterfly landing on a warm stone.", "Jon Kabat-Zinn", "Coming to Our Senses"),
    Quote("No moment is merely a bridge to the next moment; this one counts completely.", "Jon Kabat-Zinn", "Arriving at Your Own Door"),
    Quote("Between stimulus and habitual reaction lies the quiet sanctuary of mindful awareness.", "Jon Kabat-Zinn", "Full Catastrophe Living"),
    Quote("Pause at doorways, before calls, and between tasks—tiny sanctuaries stitched into ordinary hours.", "Jon Kabat-Zinn", "Arriving at Your Own Door"),
    Quote("Nothing extraordinary is required; waking up to the ordinary is extraordinary enough.", "Jon Kabat-Zinn", "Falling Awake"),

    # --- Shunryu Suzuki (35) ---
    Quote("In the beginner’s mind there are many possibilities, but in the expert’s mind there are few.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Each of you is perfect the way you are… and you can use a little improvement.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Leave your front door and your back door open. Let thoughts come and go. Just don’t serve them tea.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("When you do something, you should burn yourself completely, like a good bonfire, leaving no trace of yourself.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Calmness of mind does not mean you should stop your activity. Real calmness should be found in activity itself.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("The best way to control people or your own wild mind is to give them a wide, spacious pasture.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Everything changes; nothing stays the same—and in accepting that truth wholeheartedly, we find composure.", "Shunryu Suzuki", "Not Always So"),
    Quote("What we call ‘I’ is just a swinging door which moves when we inhale and when we exhale.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Treat every single thing—your bowl, your shoes, your desk—as your own eyes.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Without accepting the fact that everything changes, we cannot find perfect composure.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Do not try to force results; sit steadily as a cedar tree in gentle rain, and soak all the way through.", "Shunryu Suzuki", "Not Always So"),
    Quote("Walking in thin mist, you do not notice getting wet, yet little by little your robe is moistened with wisdom.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("True practice is to do one thing at a time with complete sincerity, without looking sideways for praise.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Our effort should not be aimed at attaining something special, but at expressing our true nature right now.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("To give your sheep or cow a large, spacious meadow is the surest way to care for it.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Even when waves are rough on the surface, deep water beneath remains undisturbed.", "Shunryu Suzuki", "Not Always So"),
    Quote("When you bow, just bow; when you sip water, just sip water—nothing left over.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Mistakes in practice are themselves stepping-stones when met with upright, unhurried posture.", "Shunryu Suzuki", "Branching Streams"),
    Quote("Life is like stepping onto a boat which is about to sail out to sea and sink—so sing wholeheartedly!", "Shunryu Suzuki", "Not Always So"),
    Quote("If your mind is empty, it is always ready for anything; it is open to everything.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Do not be bothered by the echo of yesterday’s bell; listen to the bell ringing right now.", "Shunryu Suzuki", "Not Always So"),
    Quote("Things are not always so—holding lightly to fixed views keeps the heart supple and bright.", "Shunryu Suzuki", "Not Always So"),
    Quote("When we sit upright and breathe naturally, body and mind return home by themselves.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("There is no need to chase after enlightenment; every honest breath is already the whole universe practicing.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Like a frog sitting quietly on a lotus leaf, need nothing beyond this clear seat.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Spring flowers bloom in spring, autumn leaves fall in autumn—each season complete in its own way.", "Shunryu Suzuki", "Branching Streams"),
    Quote("Gratitude means wasting nothing, rushing nothing, and greeting each small task with warm hands.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("To study the Way is to study the self; to study the self is to forget the self and wake up to everything.", "Shunryu Suzuki", "Branching Streams"),
    Quote("Keep your spine upright and your heart soft—firmness and gentleness belong together.", "Shunryu Suzuki", "Not Always So"),
    Quote("One quiet step after another carries you farther than anxious leaps ever could.", "Shunryu Suzuki", "Not Always So"),
    Quote("In zazen, let images come and let them vanish; do not write footnotes on passing clouds.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Simplicity in your room and simplicity in your schedule make spaciousness in your mind.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Even a candle’s small glow is complete light; do not compare it with the midday sun.", "Shunryu Suzuki", "Not Always So"),
    Quote("Every morning we return to zero—fresh mind, fresh breath, fresh sky.", "Shunryu Suzuki", "Zen Mind, Beginner’s Mind"),
    Quote("Where you are right now is the exact monastery you need.", "Shunryu Suzuki", "Not Always So"),

    # --- Lao Tzu (35) ---
    Quote("Nature does not hurry, yet everything is accomplished.", "Lao Tzu", "Tao Te Ching"),
    Quote("Do you have the patience to wait till your mud settles and the water is clear?", "Lao Tzu", "Tao Te Ching"),
    Quote("A journey of a thousand miles begins beneath your feet.", "Lao Tzu", "Tao Te Ching"),
    Quote("Silence is a source of great strength.", "Lao Tzu", "Tao Te Ching"),
    Quote("When I let go of what I am, I become what I might be.", "Lao Tzu", "Tao Te Ching"),
    Quote("Nothing in the world is softer or more yielding than water, yet nothing can surpass it in wearing away stone.", "Lao Tzu", "Tao Te Ching"),
    Quote("Thirty spokes share the wheel’s hub; it is the empty center that makes the wagon move.", "Lao Tzu", "Tao Te Ching"),
    Quote("Shape clay into a vessel; it is the space within that makes the cup useful.", "Lao Tzu", "Tao Te Ching"),
    Quote("He who knows that enough is enough will always have enough.", "Lao Tzu", "Tao Te Ching"),
    Quote("Care about what other people think and you will always be their prisoner.", "Lao Tzu", "Tao Te Ching"),
    Quote("Be content with what you have; rejoice in the way things are. When you realize nothing is lacking, the whole world belongs to you.", "Lao Tzu", "Tao Te Ching"),
    Quote("The snow goose need not bathe to make itself white. Neither need you do anything but be yourself.", "Lao Tzu", "Sayings of the Tao"),
    Quote("Respond intelligently even to unintelligent treatment.", "Lao Tzu", "Tao Te Ching"),
    Quote("To the mind that is still, the whole universe surrenders.", "Lao Tzu", "Tao and Chuang Tzu"),
    Quote("Simplicity, patience, compassion—these three are your greatest treasures.", "Lao Tzu", "Tao Te Ching"),
    Quote("Fill your bowl to the brim and it will spill. Keep sharpening your knife and it will blunt.", "Lao Tzu", "Tao Te Ching"),
    Quote("Those who know do not boast; those who shine brightest walk quietly like valley streams.", "Lao Tzu", "Tao Te Ching"),
    Quote("Because the sage competes with no one, no one in the world can compete with him.", "Lao Tzu", "Tao Te Ching"),
    Quote("Living trees and grasses are supple and bending; stiffness belongs only to what has dried up.", "Lao Tzu", "Tao Te Ching"),
    Quote("Act without forcing, work without striving, savor the plain and find greatness in the small.", "Lao Tzu", "Tao Te Ching"),
    Quote("Deal with difficult things while they are still easy; tend great things while they are still small.", "Lao Tzu", "Tao Te Ching"),
    Quote("Water benefits ten thousand things without contending, resting peacefully in the low places others overlook.", "Lao Tzu", "Tao Te Ching"),
    Quote("Stop leaving and you will arrive. Stop searching and you will see.", "Lao Tzu", "Tao Te Ching"),
    Quote("Knowing others is intelligence; knowing yourself is true wisdom.", "Lao Tzu", "Tao Te Ching"),
    Quote("In pursuit of knowledge, every day something is added. In pursuit of the Tao, every day something is dropped.", "Lao Tzu", "Tao Te Ching"),
    Quote("A good traveler has no fixed plans and is not intent solely on arriving.", "Lao Tzu", "Tao Te Ching"),
    Quote("True words are not flashy; flashy words are rarely true.", "Lao Tzu", "Tao Te Ching"),
    Quote("Gentleness overcomes rigidity; quietness outlasts storms.", "Lao Tzu", "Tao Te Ching"),
    Quote("Stand rooted in the center, watch ten thousand things rise and return, and rest in peace.", "Lao Tzu", "Tao Te Ching"),
    Quote("Strong winds do not last all morning; pelting rain does not last all day.", "Lao Tzu", "Tao Te Ching"),
    Quote("Hold fast to stillness and let life’s myriad movements settle into their natural rhythm.", "Lao Tzu", "Tao Te Ching"),
    Quote("Do your work, then step back—the only path to serenity.", "Lao Tzu", "Tao Te Ching"),
    Quote("Kindness in words creates confidence; kindness in thinking creates profoundness; kindness in giving creates love.", "Lao Tzu", "Tao Te Ching"),
    Quote("Cut doors and windows for a room; it is the empty space that makes it livable.", "Lao Tzu", "Tao Te Ching"),
    Quote("Return to the uncarved block: simple, whole, unhurried, and free of pretense.", "Lao Tzu", "Tao Te Ching"),

    # --- Jack Kornfield (30) ---
    Quote("In the end, just three things matter: how well we have lived, how well we have loved, how well we have learned to let go.", "Jack Kornfield", "The Wise Heart"),
    Quote("If your compassion does not include yourself, it is incomplete.", "Jack Kornfield", "A Path with Heart"),
    Quote("The trouble is, you think you have time—so treasure this very hour with your whole heart.", "Jack Kornfield", "Buddha’s Little Instruction Book"),
    Quote("After the ecstasy, the laundry—spiritual life lives right inside sweeping the kitchen and feeding the cat.", "Jack Kornfield", "After the Ecstasy, the Laundry"),
    Quote("You can hold the joys and sorrows of this day with the same spacious tenderness.", "Jack Kornfield", "A Path with Heart"),
    Quote("Forgiveness is giving up all hope of a better past.", "Jack Kornfield", "The Art of Forgiveness"),
    Quote("Peace requires that we make a truce with uncertainty rather than waiting for all conditions to line up.", "Jack Kornfield", "No Time Like the Present"),
    Quote("Your heart is like an ancient oak: storms bend its branches, yet its roots grow deeper in quiet soil.", "Jack Kornfield", "The Wise Heart"),
    Quote("Everything that has a beginning has an ending. Make your peace with that and all will be well.", "Jack Kornfield", "Buddha’s Little Instruction Book"),
    Quote("When we drop the burden of perfection, genuine presence steps forward effortlessly.", "Jack Kornfield", "A Path with Heart"),
    Quote("You do not need to become someone else to be free; freedom starts right inside this breath.", "Jack Kornfield", "No Time Like the Present"),
    Quote("Train your mind as patiently as you would train a playful puppy—bring it back kindly, again and again.", "Jack Kornfield", "A Path with Heart"),
    Quote("Beneath every anxious thought is a heart simply trying to stay safe; greet it with warmth.", "Jack Kornfield", "The Wise Heart"),
    Quote("Steadiness is cultivated in small moments: pausing before speaking, softening the jaw, feeling the earth.", "Jack Kornfield", "A Lamp in the Darkness"),
    Quote("Joy is not the denial of sorrow; it is the resilient music of an undefeated spirit.", "Jack Kornfield", "No Time Like the Present"),
    Quote("No matter how long you have been distracted, waking up takes only a single sincere breath.", "Jack Kornfield", "A Path with Heart"),
    Quote("Let your life move at the pace of trust rather than the pace of alarm.", "Jack Kornfield", "No Time Like the Present"),
    Quote("Wisdom says we are nothing; love says we are everything. Between the two, our life flows.", "Jack Kornfield", "A Path with Heart"),
    Quote("Step outside and look up at the stars or trees; let vastness recalibrate your worries.", "Jack Kornfield", "The Wise Heart"),
    Quote("Listening generously without rushing to fix is one of the rarest medicines on earth.", "Jack Kornfield", "A Lamp in the Darkness"),
    Quote("Every season of life—blooming, resting, shedding leaves—belongs to the path.", "Jack Kornfield", "After the Ecstasy, the Laundry"),
    Quote("Freedom is the capacity to love this imperfect world without losing your center.", "Jack Kornfield", "No Time Like the Present"),
    Quote("Soften your belly, drop your shoulders, and remember you don’t have to carry the whole sky.", "Jack Kornfield", "A Path with Heart"),
    Quote("Gratitude turns an ordinary meal into a feast and an ordinary afternoon into a sanctuary.", "Jack Kornfield", "The Wise Heart"),
    Quote("Even small acts of patience ripple outward farther than our eyes can trace.", "Jack Kornfield", "A Lamp in the Darkness"),
    Quote("Meet today’s tasks with dignity and lightness, like tending a quiet garden.", "Jack Kornfield", "After the Ecstasy, the Laundry"),
    Quote("Nobility of spirit is measured not by never falling, but by how gently we begin again.", "Jack Kornfield", "The Wise Heart"),
    Quote("Quietness is always available one breath beneath the surface chatter.", "Jack Kornfield", "No Time Like the Present"),
    Quote("When we stop fighting reality, our energy becomes available for creativity and care.", "Jack Kornfield", "A Path with Heart"),
    Quote("May you sit at ease in the middle of your own life, right here, today.", "Jack Kornfield", "A Lamp in the Darkness"),

    # --- Tara Brach (30) ---
    Quote("Perhaps the biggest tragedy of our lives is that freedom is possible, yet we pass our years trapped in the same old patterns.", "Tara Brach", "Radical Acceptance"),
    Quote("Radical acceptance is the willingness to experience ourselves and our lives as it actually is right now.", "Tara Brach", "Radical Acceptance"),
    Quote("Pause, recognize what is happening inside, allow it to be here, and meet it with kindness.", "Tara Brach", "Radical Compassion"),
    Quote("Fear dissolves when held in the warm, unhurried light of mindful presence.", "Tara Brach", "True Refuge"),
    Quote("There is something wonderfully bold and liberating about saying yes to our entire imperfect and messy life.", "Tara Brach", "Radical Acceptance"),
    Quote("Instead of asking ‘What is wrong with me?’, try asking gently: ‘What is this part of me needing right now?’", "Tara Brach", "Radical Compassion"),
    Quote("You can never hate or criticize yourself into lasting peace; warmth is what unlocks change.", "Tara Brach", "Radical Acceptance"),
    Quote("The sacred pause interrupts autopilot and returns us to our living, breathing heart.", "Tara Brach", "Radical Acceptance"),
    Quote("Like ocean waves settling back into deep water, thoughts quiet naturally when we stop resisting them.", "Tara Brach", "True Refuge"),
    Quote("True refuge is not a fortress where nothing can touch us; it is the awake openness that nothing can harm.", "Tara Brach", "True Refuge"),
    Quote("Place a hand gently over your heart and breathe—your nervous system understands kindness immediately.", "Tara Brach", "Radical Compassion"),
    Quote("Perfectionism is armor; vulnerability is the doorway back to belonging.", "Tara Brach", "Radical Acceptance"),
    Quote("Every time you notice judgment and choose curiosity instead, old habits loosen their grip.", "Tara Brach", "Radical Compassion"),
    Quote("Presence is the gift we long for from others, and the gift we can offer ourselves right now.", "Tara Brach", "True Refuge"),
    Quote("You don’t have to earn rest; rest is part of your birthright as a living being.", "Tara Brach", "Radical Acceptance"),
    Quote("When we stop rushing to the next moment, this very room fills with quiet beauty.", "Tara Brach", "True Refuge"),
    Quote("Pain met with resistance becomes suffering; pain met with tenderness becomes compassion.", "Tara Brach", "Radical Acceptance"),
    Quote("Treat yourself today the way you would treat a dear friend coming in from the rain.", "Tara Brach", "Radical Compassion"),
    Quote("Let your smile be gentle and unforced—a tiny signal to body and mind that you are safe to soften.", "Tara Brach", "True Refuge"),
    Quote("Beneath our hurry is often a fear of falling short; pause and discover you are already whole.", "Tara Brach", "Radical Acceptance"),
    Quote("Awareness plus warmth equals awakening—neither wing can fly alone.", "Tara Brach", "Radical Compassion"),
    Quote("Allow unfinished tasks to wait without turning them into verdicts on your worth.", "Tara Brach", "Radical Acceptance"),
    Quote("Even a single mindful breath creates space around whatever feels tight today.", "Tara Brach", "True Refuge"),
    Quote("Self-forgiveness clears the window so we can see the morning fresh again.", "Tara Brach", "Radical Acceptance"),
    Quote("Belonging doesn’t require fitting an ideal; you already belong to this breathing earth.", "Tara Brach", "True Refuge"),
    Quote("Notice what is pleasant right now—warmth in your hands, quiet air, steady ground beneath you.", "Tara Brach", "True Refuge"),
    Quote("Courage is staying tender in moments when habit wants us to shut down.", "Tara Brach", "Radical Compassion"),
    Quote("Unclench your hands, soften around your eyes, and let this breath be easy.", "Tara Brach", "Radical Acceptance"),
    Quote("What we meet with clear, loving attention transforms naturally in its own season.", "Tara Brach", "Radical Compassion"),
    Quote("Home is wherever your attention and your kindness meet in the present moment.", "Tara Brach", "True Refuge"),
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


def _pool_for_author(author_filter: str) -> tuple[Quote, ...]:
    if author_filter and author_filter.lower() != "all":
        matched = tuple(q for q in QUOTES if q.author.lower() == author_filter.lower())
        if matched:
            return matched
    return QUOTES


def _pool_signature(pool: tuple[Quote, ...]) -> str:
    h = hashlib.sha256()
    for q in pool:
        h.update(q.author.encode("utf-8"))
        h.update(b"\x00")
        h.update(q.text.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:16]


def _build_shuffled_order(pool: tuple[Quote, ...], recent_indices: list[int], spread_authors: bool) -> list[int]:
    """Create a CSPRNG Fisher-Yates shuffled index order without boundary repeats or author clumping."""
    n = len(pool)
    order = list(range(n))
    _SYS_RNG.shuffle(order)

    if n <= 2:
        return order

    # Push any recently seen quotes out of the opening window of the new deck
    guard = min(len(recent_indices), max(1, n // 3), 30)
    recent_set = set(recent_indices[-guard:])
    if recent_set:
        front_safe = [idx for idx in order if idx not in recent_set]
        front_recent = [idx for idx in order if idx in recent_set]
        # Place safe items first, then mix recent items randomly into the back two-thirds
        split = max(1, len(front_safe) // 3)
        head = front_safe[:split]
        tail = front_safe[split:] + front_recent
        _SYS_RNG.shuffle(tail)
        order = head + tail

    # De-clump consecutive identical authors when viewing all teachers
    if spread_authors and n >= 6:
        for i in range(1, n):
            if pool[order[i]].author == pool[order[i - 1]].author:
                for j in range(i + 1, min(n, i + 14)):
                    if pool[order[j]].author != pool[order[i - 1]].author:
                        order[i], order[j] = order[j], order[i]
                        break

    return order


class QuoteDeck:
    """Persistent non-repeating shuffled quote & buddy dealer."""

    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = state_path
        self._state: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self.state_path and self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {"decks": {}, "buddy_order": [], "buddy_pos": 0, "last_buddy": -1}

    def _save(self) -> None:
        if not self.state_path:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
            os.replace(tmp, self.state_path)
        except Exception:
            pass

    def next_quote_and_buddy(
        self,
        author_filter: str = "all",
        buddy_mode: str = "auto",
        advance: bool = True,
    ) -> tuple[Quote, ZenBuddy]:
        pool = _pool_for_author(author_filter)
        key = (author_filter or "all").lower()
        sig = _pool_signature(pool)
        decks = self._state.setdefault("decks", {})
        entry = decks.get(key)

        spread = key == "all"
        if (
            not isinstance(entry, dict)
            or entry.get("sig") != sig
            or not isinstance(entry.get("order"), list)
            or len(entry["order"]) != len(pool)
        ):
            order = _build_shuffled_order(pool, [], spread_authors=spread)
            entry = {"sig": sig, "order": order, "pos": 0, "recent": [], "current_idx": order[0]}
            decks[key] = entry

        if not advance and isinstance(entry.get("current_idx"), int) and 0 <= entry["current_idx"] < len(pool):
            q_idx = int(entry["current_idx"])
        else:
            pos = int(entry.get("pos", 0))
            order = entry["order"]
            if pos >= len(order):
                recent = list(entry.get("recent", []))
                order = _build_shuffled_order(pool, recent, spread_authors=spread)
                entry["order"] = order
                pos = 0
            q_idx = int(order[pos])
            entry["pos"] = pos + 1
            entry["current_idx"] = q_idx
            recent = list(entry.get("recent", []))
            recent.append(q_idx)
            entry["recent"] = recent[-40:]

        if buddy_mode and buddy_mode != "auto" and buddy_mode in BUDDY_BY_KEY:
            buddy = BUDDY_BY_KEY[buddy_mode]
        else:
            b_order: list[int] = self._state.get("buddy_order") or []
            b_pos = int(self._state.get("buddy_pos", 0))
            last_b = int(self._state.get("last_buddy", -1))
            if not advance and 0 <= last_b < len(ZEN_BUDDIES):
                b_idx = last_b
            else:
                if len(b_order) != len(ZEN_BUDDIES) or b_pos >= len(b_order):
                    b_order = list(range(len(ZEN_BUDDIES)))
                    _SYS_RNG.shuffle(b_order)
                    if len(b_order) > 1 and b_order[0] == last_b:
                        b_order[0], b_order[1] = b_order[1], b_order[0]
                    b_pos = 0
                b_idx = int(b_order[b_pos])
                self._state["buddy_order"] = b_order
                self._state["buddy_pos"] = b_pos + 1
                self._state["last_buddy"] = b_idx
            buddy = ZEN_BUDDIES[b_idx]

        self._save()
        return pool[q_idx], buddy


_DEFAULT_DECK = QuoteDeck()


def select_quote_and_buddy(
    rotate_minutes: int = 1,
    offset: int = 0,
    author_filter: str = "all",
    buddy_mode: str = "auto",
    now_ts: float | None = None,
    deck: QuoteDeck | None = None,
    advance: bool = True,
) -> tuple[Quote, ZenBuddy]:
    """Deal the next non-repeating quote + cute Zen buddy from a shuffled deck."""
    _ = (rotate_minutes, offset, now_ts)
    active_deck = deck if deck is not None else _DEFAULT_DECK
    return active_deck.next_quote_and_buddy(
        author_filter=author_filter,
        buddy_mode=buddy_mode,
        advance=advance,
    )
