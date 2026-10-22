"""Copy for the eight /wellness/<dimension> pages. Source: docs/SOURCE_BRIEF.md with the fixes in docs/BUILD_SPEC.md
(no cost-barrier claim, no stray "Body:" labels, scheduling buttons point to Google Calendar) and docs/COPY_DRAFTS.md.

Each entry: slug, name, headline, sub, what (paragraphs), how_intro (paragraph), items ((lead, rest) pairs), plus optional
how_after (paragraph after the list), extra (a second button: (label, href)).
"""

WELLNESS = [
    dict(
        slug="emotional", name="Emotional",
        headline="Your emotions are not symptoms to be managed. They're signals to be understood.",
        sub="Emotional wellness is the foundation of everything else — and at Anavah, it's where we begin.",
        what=[
            "Emotional wellness is the ability to understand, process, and express emotions in healthy ways and to maintain resilience in the face of stress, loss, and change. It's not the absence of difficult feelings; it's the capacity to move through them without being defined by them.",
            "When emotional wellness is compromised, the effects reach everywhere. Physical pain can feel more intense. Motivation can disappear. Relationships can strain. Recovery from illness or injury can slow. The body and the emotions are not separate systems.",
        ],
        how_intro="At Anavah, emotional wellness is the starting point. Every treatment plan begins with a comprehensive psychiatric evaluation that looks at the full emotional picture — not just the presenting symptoms, but the patterns, the history, and the way your emotional health intersects with your physical wellbeing. From there, we offer:",
        items=[
            ("Psychiatric evaluation and diagnosis", "understanding what's driving the symptoms, not just naming them"),
            ("Medication management when appropriate", "calibrated to your full health picture, including physical health"),
            ("Lifestyle and stress coaching", "evidence-based strategies for regulation, recovery, and resilience"),
            ("Coordinated care", "ensuring every provider on your team understands and accounts for your emotional health"),
        ],
    ),
    dict(
        slug="physical", name="Physical",
        headline="A healthy mind requires a healthy body. We treat both.",
        sub="At Anavah, physical health is never an afterthought — it's integrated into every aspect of your psychiatric care.",
        what=[
            "Physical wellness is more than fitness or the absence of disease. It encompasses movement, nutrition, sleep, cardiovascular health, pain management, and the body's overall capacity to function, heal, and adapt. It is inseparable from mental health.",
            "Psychiatric medications can affect metabolism, weight, cardiovascular function, and exercise capacity. Chronic pain can intensify depression and anxiety. Sleep disorders can fuel mood instability. Physical injuries can trigger emotional crises. The body and mind are one system, and they must be treated as one.",
        ],
        how_intro="Every psychiatric care plan at Anavah accounts for a patient's physical health status — including active PT, OT, or physiatry treatment. We also offer:",
        items=[
            ("Exercise readiness and clearance screenings", "helping movement-based therapies be prescribed safely, with full awareness of psychiatric status and medications"),
            ("Lifestyle and movement coaching", "evidence-based guidance on physical activity calibrated to your clinical treatment plan"),
            ("Nutritional coaching", "supporting metabolic and mental health through food, aligned with your treatment goals"),
            ("Cross-provider coordination", "direct communication with your physical medicine providers to keep all treatment aligned"),
        ],
    ),
    dict(
        slug="social", name="Social",
        headline="Connection is medicine. And isolation is a clinical risk factor.",
        sub="Social wellness is a documented driver of mental and physical health, and it's a dimension Anavah takes seriously.",
        what=[
            "Social wellness is the quality of your relationships, your sense of belonging, and your ability to give and receive meaningful support. It is not about being extroverted or having a large social circle — it is about having connection that is real and sustaining.",
            "Research associates social isolation with higher rates of depression, anxiety, and cardiovascular disease, and strong social connection with better mental and physical health. It is also one of the most undervalued dimensions in traditional psychiatric care.",
        ],
        how_intro="Anavah addresses social wellness in several ways:",
        items=[
            ("Coordinated care", "patients who are seen by multiple providers often feel alone in the system, translating between doctors and managing contradictions themselves. Anavah works to reduce that isolation by keeping providers aligned and informed."),
            ("Community", "our Skool community is a peer space where patients can connect with others navigating similar healthcare journeys. It is anonymous-friendly, and it is not a place to share health details."),
            ("Lifestyle coaching", "exploring the role of social support in your recovery, identifying barriers to connection, and building strategies that fit your life."),
        ],
        community=True,
    ),
    dict(
        slug="occupational", name="Occupational",
        headline="When your health affects your work — or your work affects your health — you need care that understands both.",
        sub="Anavah supports patients navigating the intersection of mental health, physical recovery, and professional life.",
        what=[
            "Occupational wellness is the sense of engagement, purpose, and sustainable balance you find in your work and daily responsibilities. It's not just about job performance — it's about whether your work gives you meaning and whether you can show up for it without sacrificing your health.",
            "When mental health or physical injuries collide with a person's ability to work, the consequences are significant in every direction: income, identity, legal standing, and recovery trajectory can all be affected. This is territory where integrated, coordinated care matters most.",
        ],
        how_intro="Anavah's integrative approach is directly relevant to occupational health:",
        items=[
            ("Return-to-work coordination", "communicating with occupational therapists, physiatrists, and physical therapists to align treatment with realistic functional goals"),
            ("Exercise readiness screenings", "helping any movement-based intervention in your return-to-work plan be safe given your psychiatric and physical status"),
            ("Psychiatric documentation", "for personal injury cases, disability evaluations, or return-to-work clearances, Anavah provides clinical documentation. Medical and legal documentation services must occur during a session."),
            ("Employer and workplace wellness", "organizations can partner with Anavah for mental health programming, consulting, and staff training"),
        ],
        extra=("Contact Us (employer inquiries)", "/#contact"),
    ),
    dict(
        slug="environmental", name="Environmental",
        headline="Your environment shapes your mental health. Shaping it back is part of healing.",
        sub="The spaces you live, work, and move through matter more than most healthcare providers acknowledge.",
        what=[
            "Environmental wellness is the relationship between a person and their surroundings — the physical spaces they inhabit and the degree to which those spaces support or undermine their health. It encompasses sleep environment, workspace design, exposure to natural light, noise levels, safety, and access to nature. In today's day and age this also includes what you consume, not just physically but mentally. From the feeds you watch to the music you listen to, everything has an impact on your wellness.",
            "A chaotic, cluttered, or unsafe home environment can chronically elevate stress. Poor lighting can disrupt circadian rhythm and worsen mood disorders. Lack of access to green space and natural light is associated with depression and anxiety. These are not soft variables — they are clinical risk factors.",
        ],
        how_intro="Anavah addresses environmental wellness through clinically informed lifestyle coaching — not generic wellness advice:",
        items=[
            ("Sleep environment assessment", "reviewing the physical conditions affecting sleep quality, which has a direct effect on psychiatric stability"),
            ("Light and circadian health", "guidance on light exposure patterns that support mood regulation, especially relevant for patients managing depression or bipolar spectrum conditions"),
            ("Workspace and daily routine design", "practical strategies for reducing environmental stressors in work and home settings"),
            ("Coordination with physical medicine providers", "ensuring environmental modifications are aligned with any physical treatment goals"),
        ],
    ),
    dict(
        slug="intellectual", name="Intellectual",
        headline="An engaged mind is part of recovery, part of staying well, and part of feeling alive.",
        sub="Intellectual wellness is not a luxury — it's a clinical factor that can shape recovery, resilience, and long-term mental health.",
        what=[
            "Intellectual wellness is the ongoing engagement of the mind through learning, curiosity, creativity, and critical thinking. It is connected to emotional resilience, sense of purpose, professional effectiveness, and cognitive longevity.",
            "When depression, anxiety, trauma, or medication side effects blunt a person's intellectual engagement — when they can no longer concentrate, find pleasure in learning, or access the creative parts of themselves — it is both a symptom and a driver of declining wellbeing. Recovery that ignores this dimension is incomplete.",
        ],
        how_intro="Anavah takes a full-person view in psychiatric treatment — which means asking not just how a patient feels, but how they think, learn, and engage:",
        items=[
            ("Cognitive impact assessment", "understanding how symptoms and medications are affecting concentration, memory, and mental clarity"),
            ("Medication calibration", "working to minimize cognitive side effects while maintaining therapeutic benefit, in coordination with any physical providers whose treatment intersects with cognition"),
            ("Coaching on intellectual engagement", "supporting patients in protecting and rekindling the intellectual and creative pursuits that give them meaning"),
            ("Education as part of care", "helping patients understand their conditions deeply, because knowledge is itself therapeutic"),
        ],
    ),
    dict(
        slug="spiritual", name="Spiritual",
        headline="Purpose is not peripheral to healing. It's fundamental.",
        sub="Spiritual wellness at Anavah is not about religion — it's about meaning, values, and the sense that your life matters.",
        what=[
            "Spiritual wellness is the sense of meaning, purpose, and alignment between a person's values and how they live. It is not necessarily religious — though it can be. It is the experience of feeling that what you do matters, that you are connected to something larger than yourself, and that your life is moving in a direction that reflects who you are.",
            "Research consistently links a strong sense of meaning and purpose to better mental health, lower rates of depression and anxiety, greater resilience in adversity, and even improved physical health markers. This is not a peripheral dimension — it is one of the most powerful and most overlooked drivers of long-term wellbeing.",
        ],
        how_intro="The name Anavah comes from the Hebrew word for humility — the radical act of accepting your strengths, your limitations, and your circumstances, and taking full responsibility for what you do with them. This philosophy shapes how we approach spiritual wellness with every patient. At Anavah, spiritual wellness is explored through:",
        items=[
            ("Values clarification", "helping patients identify what they care about most and how those values are being honored or violated in their current life"),
            ("Purpose-centered coaching", "building treatment plans that protect and strengthen the sources of meaning in a patient's life"),
            ("Inclusive approach", "Anavah's spiritual wellness work is grounded in clinical research, not any particular religious tradition; patients of all backgrounds and belief systems are welcome"),
        ],
    ),
    dict(
        slug="financial", name="Financial",
        headline="Financial stress is one of the most common — and most underaddressed — drivers of mental health struggles.",
        sub="Anavah treats financial stress as a real clinical factor in treatment planning.",
        what=[
            "Financial wellness is the ability to manage your resources in a way that supports security, reduces chronic stress, and allows you to pursue the life you want. It is not about wealth — it is about the relationship between your financial situation and your mental and physical health.",
            "Financial stress is among the most common contributors to anxiety, depression, and poor physical health. It affects sleep, relationships, the ability to seek and maintain treatment, and the cognitive bandwidth available for recovery. In clinical settings, it is too often bracketed off from the \"real\" conversation — and that is a mistake.",
        ],
        how_intro="Anavah addresses financial wellness on two levels.",
        items=[
            ("First,", "financial stress is recognized as a legitimate and significant factor in treatment planning. We ask about it, we talk about it, and we account for it in how we structure care. The connection between financial pressure and mental health symptoms is acknowledged — not ignored."),
            ("Second,", "financial wellness is the stability, and the stress, that comes from how we earn, spend and plan. Money worries are among the most common contributors to anxiety and poor sleep, and they can make it harder to start or stay in care. Anavah talks about financial stress openly as part of treatment planning, helps you understand your options (private pay, insurance, and superbills for out-of-network reimbursement), and explains fees on your consultation call so there are no surprises."),
        ],
        plain_items=True,
    ),
]

BY_SLUG = {d["slug"]: d for d in WELLNESS}
