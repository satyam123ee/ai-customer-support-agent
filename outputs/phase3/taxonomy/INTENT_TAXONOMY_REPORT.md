# Phase 3A: AppleSupport Intent Taxonomy Discovery

## Method

This report is generated from the Phase 2 AppleSupport JSONL. The script streams customer messages, applies transparent phrase families found during corpus inspection, retains multi-intent matches, and leaves unmatched text unclassified rather than inventing a category.

## Coverage and diagnostics

- Customer messages analyzed: 119,895
- Classified messages: 72,598 (60.55%)
- Unclassified messages: 47,297 (39.45%)
- Multi-intent messages: 28,505 (23.77%)
- Too-short messages: 9,306 (7.76%)
- Non-support-like messages: 619 (0.52%)

## Proposed taxonomy

### Software and operating-system updates (`software_update_os`)

Problems installing, using, or recovering from iOS, macOS, or software updates.

- Primary examples: 33,170 (27.666% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bios\b, \bmacos\b, \bhigh sierra\b, \bsoftware update, \bupdate[ds]?\b, \bupgrade[ds]?\b, \bbeta\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1000115` — @AppleSupport I’m continually getting the “Could Not Activate iPhone” message … any updates on when this will be working?
  - `1000205` — @115858 is buggy. My dock is gone on iOS 11 #Appleisdoomed https://t.co/l3tFt7DaPc
  - `1000223` — Wth @115858, I've been clicking "download &amp; install" for almost a week now but the update doesn't want to start download. 🤔
  - `1000229` — @AppleSupport Please. Let the people in charge of the updates to fix the battery issue. Last two iOS updates worsen the battery life.
  - `1001114` — @AppleSupport after updating to iOS 11.0.3, my iPhone 7 will randomly freeze on any app/screen. The buttons won’t even work

### Battery, power, and charging (`battery_power_charging`)

Battery-life, charging, power-on/off, or unexpected shutdown concerns.

- Primary examples: 6,273 (5.232% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bbattery\b, \bcharg(?:e|ing|er)\b, \bpower\b, \bshut ?down\b, \bturn(?:ed)? off\b, \bwon'?t turn on\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1000219` — @AppleSupport any way to check overall battery health of my iPhone 7?
  - `1001152` — Well ios11 is a swarm of bugs. I literally was stranded in a foreign country because my battery suddenly died. @AppleSupport
  - `1001150` — @AppleSupport The battery dies in seconds. I’ve contacted my company IT department and they stated it is a known 11.3 issue.
  - `1001171` — @AppleSupport ios 11.0.3 tons of bugs on my iphone 5s, battery drains while charging, no clock or date on lock screen, visual artifacts
  - `1001221` — @AppleSupport I close my MacBook Pro at night,but I found that it would automatically shut down. What happened?

### Connectivity and network access (`connectivity_network`)

Wi-Fi, Bluetooth, cellular, hotspot, signal, or network connection problems.

- Primary examples: 2,550 (2.127% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bwi[ -]?fi\b, \bbluetooth\b, \bcellular\b, \bnetwork\b, \bhotspot\b, \bsignal\b, \b4g\b, \blte\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1001123` — @AppleSupport where is personal hotspot in iPhone 7? https://t.co/qh3l74Q2Sl
  - `1001121` — @AppleSupport Hotspot is related to carrier? Thats something new.
  - `1001122` — @AppleSupport My carrier BSNL allows hotspot. Please tell me what should I do now?
  - `1001134` — @115858 if my screen say poor connection does that mean my wifi is messed up or theres? cause i tired of having this argument erry night 😭💯
  - `1001180` — @AppleSupport enfia no cu essa atualização maldita que fica ligando o Wi-Fi sozinho

### Apple ID, iCloud, and account access (`apple_id_icloud_account`)

Apple ID, iCloud, sign-in, password, verification, or account-access concerns.

- Primary examples: 2,945 (2.456% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bapple id\b, \bicloud\b, \bsign[ -]?in\b, \bpassword\b, \baccount\b, \bverification\b, \btwo[ -]?factor\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1000151` — @AppleSupport @AppleSupport, link not helpful - Issue was getting the Zip, SS# AT&amp;T verification- Is that Apple's Servers or AT&amp;T? #transparency #iphoneX
  - `1002979` — @AppleSupport hello, I just got an email saying that my apple ID has been disabled. Can you confirm that email? I'm afraid it might be fake.
  - `1003753` — @AppleSupport I’m getting the following error when trying to access my Apple ID - iPhone 6s plus (11.0.3). HELP!! https://t.co/qPPhunkwEs
  - `1003751` — @AppleSupport No - just this one. Steps taken: App Store / Account / Apple ID. The error occurs on https://t.co/g3FtgcjJhZ.
  - `1005212` — @AppleSupport hi guys Could you please DM me to discuss an issue I'm having with account recovery please? I'm getting really annoyed now 😭

### App Store and Apple media services (`app_store_media_services`)

App Store, iTunes, Apple Music, podcasts, downloads, or media-library issues.

- Primary examples: 4,844 (4.040% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bapp store\b, \bitunes\b, \bapple music\b, \bmusic\b, \bpodcast\b, \bdownload(?:ing|ed)?\b, \blibrary\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1000221` — @AppleSupport Apps weren't a problem, System update was. I was able to download &amp; install the system update via iTunes just after I sent the tweet.
  - `1002272` — @AppleSupport if I restore a previous itunes backup onto a new device, will all my apps be automatically logged in?
  - `1002785` — @AppleSupport my iPhone has 6GB available but will not allow me to download apps or take any photos. WHAT GIVES https://t.co/pAhLWXleQ9
  - `1002936` — @AppleSupport my iPhone got stuck while restoring it via itunes could you please help as your web services is down?
  - `1002957` — #iOS11.0.3 @AppleSupport This update is STILL full of bugs😡Apple music won’t work &amp;I’m paying $$$ For subscription. Please fix ASAP

### Billing, purchases, and subscriptions (`billing_purchases_subscriptions`)

Charges, payments, refunds, purchases, subscriptions, or card-related support.

- Primary examples: 1,395 (1.164% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bcharged\b, \bcharge(?: me| my| for)\b, \bbill(?:ing|ed)?\b, \bpayment\b, \bpurchase[ds]?\b, \brefund\b, \bsubscription\b, \bcredit card\b, \bmoney\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1005006` — @AppleSupport It appears that the other option(whatever that may be)is not available to customers using a 5 month old faulty phone,that only works on low brightness,consequently damaging them eyes!Great to see you looking after your customers Apple👍May have to send you my opticians bill 👓🤔
  - `1005226` — @AppleSupport I did it before, they are not helping, they say I have to wait until Apple see the bill. It is my 3th day without phone
  - `1007803` — @AppleSupport Who are these people? How did they access my phone to input their info if my phone isn’t hacked. Not just for my payment info. But, https://t.co/Ommd2RFJs8
  - `1008526` — @AppleSupport i cancelled it a day before and it still charged me
  - `101239` — @115858 Just because you're releasing new phones doesn't mean you should stop making my current iPhone stop working. I have a contract and cannot just purchase a new phone every 12 months.

### Messages, calls, and FaceTime (`messaging_calls_facetime`)

iMessage, SMS/message delivery, calls, or FaceTime problems.

- Primary examples: 3,348 (2.792% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bimessage\b, \bface ?time\b, \bsms\b, \btext(?:ing|s)?\b, \b(?:send|sent|receive|received|deliver(?:ed|y)?)\s+(?:a )?messages?\b, \bmessages?\s+(?:not|won|doesn|aren|isn't|are not|can't)\b, \bcalls?\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1000217` — @AppleSupport my iPhone 7 isn't sending or receiving iMessages and I can't make or receive phone calls. Tried doing a reset multiple times
  - `1001128` — @AppleSupport my mother received this phishing text message a few days ago. I assume you’re aware of the scam, but the website obviously needs to be stopped. https://t.co/u2pP8gTJ8I
  - `1002307` — @AppleSupport Yes I've sent a message. Please check @AppleSupport
  - `1002314` — @AppleSupport this is a screenshot from iMessage. I am missing the space bar. Are you aware of this problem? Should I open a bug report? https://t.co/RfUKpKIELC
  - `1005223` — Do you know about this; @115858 @AppleSupport ? Obviously it's a scam, and I've received similar emails, but never a text before. https://t.co/qIL5efcjoo

### Hardware, display, and accessories (`hardware_accessories`)

Physical device, screen, camera, audio, button, port, cable, or accessory problems.

- Primary examples: 3,568 (2.976% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bscreen\b, \bcamera\b, \bspeaker\b, \bheadphones?\b, \bhome button\b, \btouch id\b, \blightning\b, \bcable\b, \bport\b, \bmicrophone\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1001130` — @AppleSupport my iPhone 7 Plus doesn’t work properly with 11.0.3 😡😡. The speaker doesn’t work on calls, is non responsive &amp; screen locks!!
  - `1002023` — @AppleSupport this screen freezing in the horizontal is absolutely unacceptable. Please see the MANY complaints on this.
  - `1002228` — So my iPhone is once again back in Headphone mode for absolutely no fucking reason. Thanks @115858.
  - `1002258` — @AppleSupport When I screen record and edit the video in iMovie, the sound goes missing. The microphone is turned on, and I can hear it when played inside the photo library. But not in imovie. Any fix?
  - `1002793` — @AppleSupport It’s happened with several apps and it’s happened while in a resting state, where I can feel the haptic button but screen won’t wake up.

### Device setup, activation, and migration (`device_setup_activation_migration`)

Setting up, activating, restoring, transferring, or replacing an iPhone/iPad/device.

- Primary examples: 1,640 (1.368% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bactivat(?:e|ion|ed)\b, \bset ?up\b, \brestore\b, \btransfer\b, \bmigrat(?:e|ion)\b, \bnew (?:iphone|ipad|phone)\b, \breplacement\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1000099` — @AppleSupport my iPhone X keeps getting a "Could Not Activate iPhone" error. Is the activation server down?
  - `1001166` — @115858 this new phone software is making my phone slow and glitchy! Not impressed!
  - `1003857` — Tried everything apart from restore to fix the #message send failure on #iOS11 but nothing works @AppleSupport any tips?? #bugs #issues https://t.co/H2FWpi5lxY
  - `1004998` — Apple sucks... brand new iPhone crashes every fucking day @115858
  - `1005007` — Hi @AppleSupport I hav a faulty phone,only 5 months old!Spoke to your support team who hav tried helping but I hav a hardware issue, so a replacement is my only option!I dont live near a store,sending away is not a option,I need to b contactable!What other options do apple have?

### Mac computer support (`mac_computer`)

Mac, MacBook, iMac, or desktop/laptop concerns not primarily described as an OS update.

- Primary examples: 1,344 (1.121% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bmacbook\b, \bimac\b, \bmac\b, \bmac mini\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1000208` — Seriously @115858 I LITERALLY have trouble doing anything on my 12 month old MacBook Air, transferring files, that'll be two crashes....
  - `100243` — @AppleSupport I have tried restarting my macbook but it keeps lagging. I will try rebooting and close all apps once again.
  - `1004993` — 30+ minutes on the phone with @115858 Support &amp; they ain’t do shiiiiittt to fix my Mac 😤
  - `1010562` — Does anyone have a workable way of getting photos from an iPhone6 to an iMac that actually works or have @115858 really turned to shit?
  - `101251` — @AppleSupport why is my MacBook doing this https://t.co/wpJegaDLPw

### Apple Watch support (`apple_watch`)

Apple Watch or watchOS concerns.

- Primary examples: 579 (0.483% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bapple watch\b, \bwatchos\b, \bmy watch\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1003735` — @115858 @AppleSupport do you offer a military discount on Apple Watch 3 Series?
  - `1004995` — I’m scared to wear my Apple Watch because yesterday it spontaneously called 911 four times and I had to repeatedly explain to the police that I was not in need of their assistance @115858
  - `1005016` — @AppleSupport my Apple Watch keeps going into airplane mode. What’s up with that?
  - `1005245` — @AppleSupport Hey Apple. When Will Apple-Sim for the Apple watch series 3 be supported in the Netherlands? When will Vodafone support it????
  - `1009308` — @AppleSupport is there a way to disable this feature on the Apple Watch? Prefer to see my watch face. https://t.co/bLt9tMmRJJ

### Performance, stability, and unexpected behavior (`performance_stability`)

Slow, frozen, crashing, stuck, glitching, or otherwise non-working behavior without a more specific primary issue.

- Primary examples: 4,734 (3.948% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bslow\b, \bfreez(?:e|ing|es|en)\b, \bcrash(?:es|ed|ing)?\b, \blag(?:gy)?\b, \bglitch\b, \bstuck\b, \bnot working\b, \bdoesn'?t work\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1000235` — @AppleSupport updated my phone the other day and it keeps freezing so I have to restart it. Then it’s really slow. Sort it out.
  - `1001174` — @188 app is constantly crashing on #iOS11 @AppleSupport @115858 Haptic feedback is still not working even in 11.0.3 on my 7Plus #apple
  - `100242` — @AppleSupport for now I just restarted, it doesn't lag yet. I will let you know when it happen again.
  - `1002794` — @115858 @AppleSupport iPhone 7+ iOS11 is 💩. Randomly freezing or in some cases rebooting. Please fix. #ios11update #dontupdate
  - `1002950` — @AppleSupport It’s constantly freezing! All apps. It happened just now with @118189 and the #Twitter app closed before it opened. Why?? #apple #ipone

### Keyboard, characters, and text rendering (`keyboard_text_rendering`)

Question-mark boxes, missing letters, keyboard, emoji, or character-rendering problems.

- Primary examples: 4,458 (3.718% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bquestions? marks?\b, \bsquares?\b, \bkeyboard\b, \bletters?\b, \bcharacters?\b, \bemojis?\b, \btext rendering\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1000018` — CANT STAND THOSE DAMN SQUARES, @115858 . Y’all need to fix that shit.
  - `1000024` — I’m so tired of these question mark boxes on my TL. Get your shit together @115858 @AppleSupport
  - `1000074` — FUCK YOU @115858 &amp; @123765! NOW I️ CAN’T TWEET THE LETTER I️?!
  - `1000080` — Why is shit popping up as questions marks on my phone?? What’s going on @AppleSupport
  - `1000109` — Dear @115858, WTF is going on with my keyboard and this “I️” bull-ish 😡

### Support contact and service experience (`support_contact_experience`)

Waiting, disconnection, direct-message, or customer-service contact problems rather than a specific product issue.

- Primary examples: 628 (0.524% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bcustomer service\b, \bon hold\b, \bdisconnected\b, \bprivate messages?\b, \bcheck dm\b, \bwaiting\b, \bsupport (?:is|was|has)\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1000092` — @AppleSupport your c/s sucks, I was just disconnected after waiting on hold for 45+ minutes
  - `1001125` — @AppleSupport Pls check DM
  - `1002970` — Been waiting for the #iPhoneX but my phone been restarting in the middle of conversation @115858 #WhatsTheDeal #FixThis
  - `1007115` — @AppleSupport what to do ? Im still waiting.
  - `1013011` — @AppleSupport I'm waiting.

### Store, order, delivery, and repair service (`store_orders_repairs`)

Apple Store, repair, Genius Bar, order, delivery, shipping, or appointment concerns.

- Primary examples: 1,122 (0.936% of all customer messages)
- Inclusion: Customer message contains one or more observed corpus evidence patterns: \bapple store\b, \brepair\b, \bgenius bar\b, \border\b, \bdeliver(?:y|ed)?\b, \bship(?:ping|ped)?\b, \bappointment\b
- Exclusion: No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.
- Representative real customer messages:
  - `1002265` — @AppleSupport thanks ios11 for making my iPhone 7 a brick. Now I have to pay $319 to repair a problem Apple created. #bootloop #ios11
  - `1011806` — @AppleSupport Apple store!
  - `101282` — Hey @AppleSupport could you make it more impossible and frustrating to get a Genius Bar Reservation for an elderly person? Ridiculous.
  - `1022926` — @AppleSupport How long will you hold on to an order for me to collect?
  - `1022925` — @AppleSupport I want to order a case and it says collect Monday but I work be able to till Tuesday. Is this ok?

## Readiness

- RAG retrieval: Sufficient volume for later retrieval experiments; use the prepared conversations and preserve direct-link limitations.
- Automated response generation: Sufficient historical customer-to-brand volume, but later work must separate safe answerable cases from cases requiring escalation.
- Escalation decisions: Potentially sufficient for discovery, but no escalation labels have been created in this phase.
- 150–250 example golden evaluation set: Sufficient source volume; a stratified, human-labelled set must still be created separately and is not produced here.

## Scope boundary

No RAG system, embeddings, LLM agent, golden set, or evaluation harness was built in this phase.
