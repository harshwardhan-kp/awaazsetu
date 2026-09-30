# Community drill kit

Purpose: test whether residents can submit understandable reports and receive acknowledgement/updates in their preferred language. This is a scripted exercise with no real distress or rescue dispatch. Coordinate the visit through the guide and community representative; those people-facing steps remain with the team.

## Session

- Brief20min: identify the drill visibly, explain privacy/AI processing and voluntary participation, show reporting number/web form, assign anonymous participant IDs and scenario cards.
- Exercise45min: participants send in their own words; coordinators inspect source messages, clarify landmarks and update ticket status.
- Debrief20min: collect ease/language/feedback ratings, note failures and assistance.

## Participation notice template

English: This is a voluntary flood-reporting practice exercise. No rescue team will be dispatched. Your report and optional recording will be processed by the private coordination team and, when configured, an AI service for transcription/extraction. Avoid names, identity documents and unrelated personal information. Optional phone details are stored encrypted for replies; area alerts require JOIN and can be stopped with STOP. You may decline or stop participating. Contact the project team to request deletion of your drill report. Application reports expire after90days; backups/provider records need their own retention handling.

Marathi: हा ऐच्छिक पूर-माहिती सराव आहे. बचाव पथक पाठवले जाणार नाही. तुमचा अहवाल आणि ऐच्छिक आवाज खाजगी समन्वयक तपासतील; AI सेवा सुरू असल्यास लिप्यंतरण आणि माहिती काढण्यासाठी वापरली जाईल. नावे, ओळखपत्रे आणि अनावश्यक वैयक्तिक माहिती देऊ नका. परिसर सूचनांसाठी JOIN आवश्यक आहे; STOP ने त्या बंद होतात. तुम्ही सहभागी होण्यास नकार देऊ शकता किंवा थांबू शकता. अहवाल हटवण्यासाठी प्रकल्प गटाशी संपर्क करा.

Hindi: यह स्वैच्छिक बाढ़-रिपोर्टिंग अभ्यास है। कोई बचाव दल नहीं भेजा जाएगा। आपकी रिपोर्ट और वैकल्पिक आवाज़ निजी समन्वयक देखेंगे; AI सेवा चालू होने पर लिप्यंतरण और जानकारी निकालने के लिए उपयोग होगा। नाम, पहचान दस्तावेज और अनावश्यक निजी जानकारी न दें। क्षेत्र सूचनाओं के लिए JOIN जरूरी है; STOP से वे बंद होती हैं। आप भाग लेने से मना कर सकते हैं या कभी भी रुक सकते हैं। रिपोर्ट हटाने के लिए परियोजना टीम से संपर्क करें।

Have the team/guide review these translated notices with fluent participants before use. Record consent separately from report content; do not make public participant/contact lists.

## Scenario cards

1. Ekta Nagar: water enters a home, waist deep, elderly person unable to leave. Send an SMS/voice/web report in the participant's own words.
2. Warje: road has knee-deep water; no trapped people. Negative facts test false urgency.
3. Dattawadi: sick elderly person needs medicine; location is a known neighborhood.
4. Karve Nagar: two children trapped; chest-deep water.
5. Unknown landmark: participant omits area; coordinator requests clarification and participant supplies Warje.
6. Repeat event: three consenting participants describe one precise GPS-backed simulated incident, each using a different language/channel. Check merging; approximate-area reports should remain separate for human review.
7. Negation: participant says nobody trapped and no water in homes; verify extraction does not claim a rescue.
8. JOIN/STOP: after SIM setup, subscribe to own area in Marathi/Hindi, queue a controlled drill alert, then STOP and confirm no further area alerts.

## Evaluation

Use held-out messages not used to tune keywords/prompts. Two fluent labellers independently annotate type, urgency class, place phrase, coordinates if known, and duplicate pairs; record disagreements and adjudication. WER requires human reference transcripts of real Marathi/Hindi audio, including noisy clips. Latency requires actual gateway timestamps from inbound SMS to handset acknowledgement, not simply API response time. Record failures, sample counts, assistance and provider configuration. Never substitute synthetic-suite accuracy for community performance.

The provided CSV templates contain no personal data. Keep any actual filled participant/test files private and out of the repository. Capture photos only with separate consent.
