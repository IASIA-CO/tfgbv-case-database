#!/usr/bin/env python3
"""
Generate realistic synthetic case records for demos and dashboard development.

    python3 scripts/seed_realistic_data.py              # 180 cases
    python3 scripts/seed_realistic_data.py --count 400
    python3 scripts/seed_realistic_data.py --purge      # remove everything it created

SYNTHETIC DATA — READ THIS
--------------------------
Every record here is invented. No row describes a real person, a real organisation, or
a real incident. Names in the PII tables are deliberately non-human ("SYNTHETIC
Survivor 042") so a generated record can never be mistaken for, or coincidentally
resemble, a real case. Every case carries SYNTHETIC_MARK and is listed in a manifest,
so --purge removes them completely before real data is loaded.

HOW THIS DIFFERS FROM seed_demo_data.py
---------------------------------------
seed_demo_data.py draws every field independently. That gives each individual chart a
plausible shape but makes cross-tabulations nonsense: sextortion cases come out
"minimal" severity, ex-partners appear as often as strangers in image-abuse cases, and
resolved cases are as likely to be last week's as last year's. A dashboard built on it
looks right until someone filters.

This script generates from CASE ARCHETYPES instead. Each archetype is a coherent bundle
— harassment types, platforms, perpetrator relation, severity, interventions, survivor
profile, and narrative — drawn from documented TFGBV patterns. Fields correlate the way
they do in real casework:

  * severity follows the harassment type, not chance
  * ex-partners dominate image-based abuse; strangers dominate public pile-ons
  * journalists and activists attract coordinated attacks, not random ones
  * interventions match the harm (account recovery for takeovers, legal referral for
    sextortion) rather than being sampled from one flat pool
  * old cases are mostly closed, recent ones mostly open
  * intake spikes during the 16 Days of Activism, as awareness campaigns drive reports

The content is invented; the SHAPE is modelled on reality. That is what makes it useful
for testing dashboards, permissions, and reports.
"""
import argparse
import datetime as dt
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seed_schema as s  # noqa: E402

SYNTHETIC_MARK = "[SYNTHETIC TEST DATA]"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "docs", "realistic_manifest.json")

WINDOW_DAYS = 540

# Invented organisations. Generic descriptors, not real bodies — but named and coded the
# way a real deployment's partner list is, so org filters and per-org reports have
# something with structure to chew on.
ORGANIZATIONS = [
    ("Digital Safety Response Desk",      "DSRD", 46),
    ("Provincial Women's Support Network", "PWSN", 20),
    ("Youth Online Rights Collective",    "YORC", 14),
    ("Media Freedom Support Unit",        "MFSU", 12),
    ("National TFGBV Helpline",           "NTH",   8),
]


def pick(weighted):
    values, weights = zip(*weighted)
    return random.choices(values, weights=weights, k=1)[0]


def pick_many(weighted, lo, hi):
    n = min(random.randint(lo, hi), len(weighted))
    chosen = []
    guard = 0
    while len(chosen) < n and guard < 200:
        guard += 1
        v = pick(weighted)
        if v not in chosen:
            chosen.append(v)
    return chosen


def m2m(field_key, values):
    return {"create": [{field_key: {"id": v}} for v in values],
            "update": [], "delete": []}


# ------------------------------------------------------------------------- archetypes
# Each entry is a coherent case pattern. Weights are relative frequencies.
# Keys not set on an archetype fall back to DEFAULTS below.

DEFAULTS = {
    "case_type": "tfgbv",
    "perp_prob": 0.80,
    "evidence_prob": 0.35,
    "pii_prob": 0.60,
    "perp_pii_prob": 0.30,
    "perp_gender": [("male", 62), ("female", 8), ("prefer_not_to_say", 30)],
    "gender": [("female", 78), ("lgbtqia_community", 5), ("transgender", 3),
               ("lesbian", 3), ("gender_diverse_group", 3), ("bisexual", 2),
               ("prefer_not_to_say", 6)],
    "reporters": [("survivor_self", 46), ("operator_outreach", 20),
                  ("partner_organization", 12), ("family_or_friend", 9),
                  ("hotline", 7), ("anonymous", 4), ("unknown", 2)],
    "identities": [("public_user", 40), ("gender_advocate", 12), ("educator", 8),
                   ("cso_member", 10), ("unknown", 8), ("minority", 5),
                   ("people_with_disabilities", 4), ("public_figure", 6),
                   ("critic", 7)],
    "ident_count": (1, 2),
    "harass_count": (1, 2),
    "platform_count": (1, 2),
    "interv_count": (2, 3),
}

ARCHETYPES = [
    {
        "key": "coordinated_pileon", "weight": 16,
        "harass": [("misogynistic_hate_speech", 40), ("cyber_bullying", 30),
                   ("discrimination", 12), ("doxxing", 10),
                   ("mass_reporting_to_silence_victims", 8)],
        "harass_count": (2, 3),
        "platforms": [("facebook", 55), ("tiktok", 15), ("youtube", 12),
                      ("x", 8), ("telegram", 10)],
        "platform_count": (1, 3),
        "relations": [("stranger", 52), ("political_actor", 30),
                      ("not_applicable", 10), ("authorities_government_officials", 8)],
        "severity": [("moderate", 34), ("high", 30), ("low", 20), ("severe", 10),
                     ("minimal", 6)],
        "interventions": [("documented", 30), ("continue_monitoring_the_case", 24),
                          ("submitted_report_to_platforms", 20),
                          ("provided_safety_guideline", 12),
                          ("mental_health_referrals", 8), ("legal_referrals", 6)],
        "interv_count": (2, 4),
        "identities": [("journalist", 22), ("political_activist", 20),
                       ("gender_advocate", 18), ("human_rights_defender", 14),
                       ("public_figure", 12), ("media_worker", 8), ("critic", 6)],
        "reporters": [("survivor_self", 34), ("operator_outreach", 28),
                      ("partner_organization", 22), ("hotline", 8), ("unknown", 8)],
        "evidence_prob": 0.62,
        "captions": [
            "Coordinated comment attack following a public post on {topic}",
            "Hate comments across {n_posts} posts on the survivor's public page",
            "Mass abusive replies after a televised interview on {topic}",
        ],
        "summaries": [
            "After publishing commentary on {topic}, the survivor received an estimated "
            "{n_comments} abusive comments across {n_posts} posts within {n_days} days. "
            "Comments were gendered and sexualised rather than engaging the substance of "
            "the post. A subset of accounts posted near-identical wording, suggesting "
            "coordination.",
            "The survivor's public page was targeted by a sustained wave of misogynistic "
            "comments after a post on {topic}. Roughly {n_accounts} accounts participated "
            "over {n_days} days, several created within the same week. Screenshots were "
            "captured before the survivor limited commenting.",
            "Following a media appearance discussing {topic}, abusive replies escalated "
            "from insults to comments about the survivor's family. The survivor reported "
            "the accounts to the platform; {n_accounts} of the reports returned no action.",
        ],
        "impacts": [
            "Reduced public posting and disabled comments on the affected account.",
            "Reported anxiety and reluctance to continue public commentary on the topic.",
            "Withdrew from an upcoming panel appearance citing safety concerns.",
            "Reported concern for family members named in the comment threads.",
        ],
    },
    {
        "key": "ncii_expartner", "weight": 12,
        "harass": [("image_video_based_abuse", 46), ("sextortion_blackmail", 20),
                   ("cyber_stalking", 14), ("cyber_bullying", 10),
                   ("physical_safety_threats", 10)],
        "harass_count": (1, 3),
        "platforms": [("telegram", 32), ("messenger", 26), ("facebook", 22),
                      ("instagram", 10), ("website", 6), ("other", 4)],
        "relations": [("ex_partner", 78), ("current_partner", 12), ("stranger", 6),
                      ("colleague", 4)],
        "severity": [("high", 40), ("severe", 30), ("moderate", 22), ("low", 8)],
        "interventions": [("submitted_report_to_platforms", 24), ("documented", 22),
                          ("legal_referrals", 18), ("mental_health_referrals", 16),
                          ("provided_safety_planning_to_victim", 12),
                          ("continue_monitoring_the_case", 8)],
        "interv_count": (3, 4),
        "perp_prob": 0.96,
        "perp_pii_prob": 0.62,
        "pii_prob": 0.78,
        "evidence_prob": 0.70,
        "reporters": [("survivor_self", 52), ("family_or_friend", 16),
                      ("hotline", 14), ("partner_organization", 10),
                      ("operator_outreach", 8)],
        "captions": [
            "Intimate photographs circulated in a group chat by a former partner",
            "Private images sent to the survivor's colleagues and relatives",
            "Private video posted to a public page following separation",
        ],
        "summaries": [
            "Approximately {n_weeks} weeks after the relationship ended, private images "
            "taken during the relationship were shared to a group chat of around "
            "{n_accounts} members. The survivor learned of the sharing from a mutual "
            "contact. The former partner denied responsibility when contacted.",
            "A former partner circulated intimate photographs to the survivor's "
            "colleagues and relatives. The images were accompanied by the survivor's "
            "workplace details. Platform reports were filed for {n_posts} separate posts.",
            "Private video content was uploaded to a public page and re-shared "
            "{n_posts} times before removal. The survivor identified the uploader as a "
            "former partner from account details visible in earlier messages.",
        ],
        "impacts": [
            "Reported severe distress and disrupted sleep; accepted a counselling referral.",
            "Took extended leave from work after colleagues received the material.",
            "Deactivated all social media accounts and changed phone number.",
            "Reported suicidal ideation at intake; escalated to mental health support.",
            "Relocated temporarily to a relative's home.",
        ],
    },
    {
        "key": "sextortion_stranger", "weight": 11,
        "harass": [("sextortion_blackmail", 50), ("image_video_based_abuse", 22),
                   ("impersonation", 16), ("cyber_stalking", 12)],
        "platforms": [("messenger", 34), ("facebook", 26), ("telegram", 22),
                      ("instagram", 10), ("whatsapp", 8)],
        "relations": [("stranger", 88), ("not_applicable", 8), ("colleague", 4)],
        "severity": [("high", 42), ("moderate", 28), ("severe", 20), ("low", 10)],
        "interventions": [("documented", 22), ("legal_referrals", 20),
                          ("submitted_report_to_platforms", 18),
                          ("provided_safety_guideline", 16),
                          ("mental_health_referrals", 12), ("2fa_setup", 12)],
        "interv_count": (2, 4),
        "perp_prob": 0.92,
        "ident_status": [("suspected", 40), ("unknown", 52), ("known", 8)],
        "evidence_prob": 0.58,
        "captions": [
            "Financial demands following a coerced video call",
            "Blackmail threats from an account posing as a recruiter",
            "Threat to publish screenshots unless payment was made",
        ],
        "summaries": [
            "The survivor was contacted by an unknown account and, after several days of "
            "friendly conversation, persuaded into a video call that was recorded without "
            "their knowledge. The account then demanded USD {amount} and threatened to "
            "send the recording to the survivor's contact list.",
            "An account presenting itself as a recruiter requested photographs as part of "
            "a supposed application process, then demanded USD {amount} to prevent their "
            "publication. The survivor did not pay. Contact continued from "
            "{n_accounts} further accounts.",
            "Following a coerced exchange of images, the survivor received demands for "
            "USD {amount} with a {n_days}-day deadline. Screenshots of the survivor's "
            "friend list were sent as proof of reach.",
        ],
        "impacts": [
            "Reported acute anxiety and fear of exposure to family.",
            "Made a partial payment before seeking help; no further contact after blocking.",
            "Reported inability to concentrate at work; accepted counselling referral.",
            "Deleted the affected account and restricted friend list visibility.",
        ],
    },
    {
        "key": "account_takeover", "weight": 13,
        "case_type": "technical_support",
        "harass": [("controlling_social_media_accounts", 54), ("impersonation", 24),
                   ("doxxing", 12), ("cyber_bullying", 10)],
        "platforms": [("facebook", 52), ("messenger", 18), ("telegram", 12),
                      ("instagram", 10), ("email", 8)],
        "relations": [("stranger", 56), ("ex_partner", 18), ("not_applicable", 14),
                      ("colleague", 8), ("current_partner", 4)],
        "severity": [("moderate", 36), ("low", 32), ("minimal", 18), ("high", 14)],
        "interventions": [("page_account_recovery", 26), ("password_reset", 24),
                          ("2fa_setup", 22), ("technical_support", 14),
                          ("secured_digital_device", 8),
                          ("provided_digital_security_training", 6)],
        "interv_count": (3, 4),
        "evidence_prob": 0.22,
        "pii_prob": 0.52,
        "reporters": [("survivor_self", 62), ("operator_outreach", 16),
                      ("partner_organization", 10), ("family_or_friend", 8),
                      ("hotline", 4)],
        "captions": [
            "Account compromised and used to message contacts",
            "Page administrator access removed by an unknown party",
            "Login from an unrecognised device followed by lockout",
        ],
        "summaries": [
            "The survivor lost access to their account after a phishing message imitating "
            "a platform security notice. The account was used to send scam messages to "
            "approximately {n_accounts} contacts before recovery. Access was restored and "
            "two-factor authentication enabled.",
            "An unknown party gained administrator access to the survivor's page and "
            "removed the survivor's own role. Recovery took {n_days} days through the "
            "platform's appeal process. Recovery contacts and app passwords were reviewed.",
            "The survivor reported a login alert from an unfamiliar location, followed by "
            "a password change they did not initiate. {n_posts} posts were published from "
            "the account before it was secured.",
        ],
        "impacts": [
            "Contacts received scam messages; survivor issued a public correction.",
            "No lasting impact reported once access was restored.",
            "Lost {n_years} years of stored messages and photographs.",
            "Reported embarrassment at content posted in their name.",
        ],
    },
    {
        "key": "impersonation_fake_profile", "weight": 10,
        "harass": [("impersonation", 52), ("doxxing", 18), ("cyber_bullying", 16),
                   ("sexual_harassment_exploitation", 14)],
        "platforms": [("facebook", 48), ("instagram", 18), ("tiktok", 14),
                      ("messenger", 12), ("telegram", 8)],
        "relations": [("stranger", 62), ("not_applicable", 16), ("ex_partner", 12),
                      ("colleague", 10)],
        "severity": [("moderate", 36), ("low", 30), ("high", 20), ("minimal", 14)],
        "interventions": [("submitted_report_to_platforms", 32), ("documented", 24),
                          ("continue_monitoring_the_case", 18),
                          ("provided_safety_guideline", 14), ("2fa_setup", 12)],
        "evidence_prob": 0.55,
        "captions": [
            "Fake profile using the survivor's photographs",
            "Duplicate profile posting sexual content in the survivor's name",
            "Impersonation account soliciting money from contacts",
        ],
        "summaries": [
            "An account was created using the survivor's photographs and name, and used "
            "to send friend requests to the survivor's contacts. At least "
            "{n_accounts} contacts were approached before the survivor was alerted. "
            "{n_posts} reports were filed with the platform.",
            "A duplicate profile posted sexual content attributed to the survivor. The "
            "survivor's employer was among the accounts it contacted. The profile was "
            "removed after {n_days} days.",
            "An impersonation account solicited money from the survivor's contacts, "
            "claiming a family emergency. {n_accounts} contacts reported receiving the "
            "request; at least one transferred funds.",
        ],
        "impacts": [
            "Contacted friends individually to warn them; reported exhaustion from doing so.",
            "Reported reputational concern with their employer.",
            "No lasting impact reported after the profile was removed.",
            "Made their photograph albums private and limited profile visibility.",
        ],
    },
    {
        "key": "stalking_threats_partner", "weight": 7,
        "harass": [("cyber_stalking", 36), ("physical_safety_threats", 30),
                   ("controlling_social_media_accounts", 18), ("cyber_bullying", 16)],
        "harass_count": (2, 3),
        "platforms": [("messenger", 32), ("facebook", 24), ("whatsapp", 16),
                      ("telegram", 16), ("signal", 6), ("other", 6)],
        "relations": [("current_partner", 44), ("ex_partner", 46), ("stranger", 6),
                      ("colleague", 4)],
        "severity": [("severe", 38), ("high", 40), ("moderate", 18), ("low", 4)],
        "interventions": [("provided_safety_planning_to_victim", 24), ("documented", 20),
                          ("legal_referrals", 18), ("secured_digital_device", 14),
                          ("mental_health_referrals", 12), ("password_reset", 6),
                          ("2fa_setup", 6)],
        "interv_count": (3, 5),
        "perp_prob": 0.98,
        "perp_pii_prob": 0.66,
        "pii_prob": 0.82,
        "ident_status": [("known", 74), ("suspected", 22), ("unknown", 4)],
        "evidence_prob": 0.50,
        "reporters": [("survivor_self", 40), ("family_or_friend", 20),
                      ("hotline", 18), ("partner_organization", 14),
                      ("operator_outreach", 8)],
        "captions": [
            "Tracking software found on the survivor's phone",
            "Continuous messaging and threats following separation",
            "Account passwords demanded by a current partner",
        ],
        "summaries": [
            "The survivor reported receiving messages referencing their location on days "
            "they had not shared it. A review of the device found a monitoring "
            "application installed under a system-sounding name. The application was "
            "removed and the device passwords reset.",
            "Following separation, the survivor received {n_messages} messages over "
            "{n_days} days, escalating to threats of physical harm if they did not "
            "return. Messages continued from {n_accounts} new accounts after blocking.",
            "A current partner required access to the survivor's account passwords and "
            "reviewed messages daily. When the survivor changed a password, threats were "
            "made against a family member. Safety planning was carried out at intake.",
        ],
        "impacts": [
            "Safety plan agreed; survivor moved to a relative's residence.",
            "Reported constant fear and avoidance of routine movements.",
            "Stopped using messaging apps entirely for several weeks.",
            "Reported the threats to local authorities with the organisation's support.",
        ],
    },
    {
        "key": "workplace_harassment", "weight": 7,
        "harass": [("sexual_harassment_exploitation", 44), ("cyber_bullying", 24),
                   ("discrimination", 18), ("cyber_stalking", 14)],
        "platforms": [("messenger", 30), ("facebook", 22), ("telegram", 20),
                      ("email", 16), ("whatsapp", 12)],
        "relations": [("colleague", 42), ("manager_supervisor", 44), ("stranger", 8),
                      ("not_applicable", 6)],
        "severity": [("moderate", 40), ("high", 26), ("low", 24), ("minimal", 10)],
        "interventions": [("documented", 28), ("legal_referrals", 20),
                          ("continue_monitoring_the_case", 18),
                          ("provided_safety_guideline", 16),
                          ("mental_health_referrals", 10),
                          ("submitted_report_to_platforms", 8)],
        "identities": [("public_user", 26), ("media_worker", 16), ("educator", 14),
                       ("cso_member", 14), ("journalist", 10), ("minority", 8),
                       ("people_with_disabilities", 6), ("unknown", 6)],
        "perp_prob": 0.94,
        "ident_status": [("known", 68), ("suspected", 26), ("unknown", 6)],
        "evidence_prob": 0.48,
        "reporters": [("survivor_self", 44), ("partner_organization", 20),
                      ("operator_outreach", 16), ("anonymous", 12), ("hotline", 8)],
        "captions": [
            "Persistent messages from a supervisor outside working hours",
            "Sexual comments in a work group chat",
            "Repeated unwanted contact from a colleague after refusal",
        ],
        "summaries": [
            "A supervisor sent the survivor messages of a sexual nature outside working "
            "hours over approximately {n_weeks} weeks. The survivor's refusals were "
            "followed by changes to their shift allocation. Messages were preserved "
            "before the survivor left the role.",
            "Sexual comments about the survivor were posted in a workplace group chat of "
            "around {n_accounts} members. Two colleagues objected; the comments "
            "continued. The survivor reported reluctance to raise it internally.",
            "A colleague continued contacting the survivor after being asked to stop, "
            "using {n_accounts} different accounts across two platforms over "
            "{n_days} days.",
        ],
        "impacts": [
            "Resigned from the position; referred for employment law advice.",
            "Requested a transfer to a different team.",
            "Reported anxiety before shifts and avoidance of the group chat.",
            "Reported feeling unable to raise the matter internally without retaliation.",
        ],
    },
    {
        "key": "youth_bullying", "weight": 9,
        "harass": [("cyber_bullying", 44), ("discrimination", 20),
                   ("misogynistic_hate_speech", 18), ("image_video_based_abuse", 10),
                   ("impersonation", 8)],
        "platforms": [("tiktok", 36), ("facebook", 24), ("instagram", 20),
                      ("messenger", 14), ("telegram", 6)],
        "relations": [("stranger", 54), ("colleague", 26), ("not_applicable", 20)],
        "severity": [("low", 36), ("moderate", 32), ("minimal", 22), ("high", 10)],
        "interventions": [("provided_safety_guideline", 26), ("documented", 22),
                          ("continue_monitoring_the_case", 20),
                          ("submitted_report_to_platforms", 16),
                          ("mental_health_referrals", 10),
                          ("provided_digital_security_training", 6)],
        "identities": [("public_user", 58), ("educator", 8), ("minority", 10),
                       ("people_with_disabilities", 8), ("indigenous_peoples", 6),
                       ("unknown", 10)],
        "gender": [("female", 82), ("gender_diverse_group", 4), ("lgbtqia_community", 4),
                   ("transgender", 2), ("queer_questioning", 3), ("prefer_not_to_say", 5)],
        "reporters": [("survivor_self", 30), ("family_or_friend", 26),
                      ("operator_outreach", 18), ("partner_organization", 14),
                      ("hotline", 8), ("anonymous", 4)],
        "perp_prob": 0.62,
        "evidence_prob": 0.30,
        "pii_prob": 0.48,
        "captions": [
            "Body-shaming comments on a short video",
            "Group chat created to mock the survivor",
            "Repeated ridicule across the survivor's videos",
        ],
        "summaries": [
            "A short video posted by the survivor attracted approximately {n_comments} "
            "comments about their appearance and weight, several from accounts appearing "
            "to belong to classmates. The survivor removed the video after {n_days} days.",
            "A group chat of around {n_accounts} members was created for the purpose of "
            "mocking the survivor, and screenshots were circulated more widely. The "
            "survivor was shown the chat by a friend.",
            "Comments ridiculing the survivor's appearance were posted across "
            "{n_posts} of their videos over {n_weeks} weeks. Reports to the platform "
            "returned no action on most of the comments.",
        ],
        "impacts": [
            "Stopped posting videos; reported reluctance to attend classes.",
            "Reported low mood and withdrawal from friends.",
            "Set account to private and removed the affected posts.",
            "No lasting impact reported at follow-up.",
        ],
    },
    {
        "key": "deepfake_ai", "weight": 5,
        "harass": [("ai_generated_sexual_content", 52), ("image_video_based_abuse", 26),
                   ("sextortion_blackmail", 12), ("cyber_bullying", 10)],
        "platforms": [("telegram", 34), ("facebook", 22), ("website", 18),
                      ("tiktok", 12), ("x", 8), ("other", 6)],
        "relations": [("stranger", 66), ("ex_partner", 16), ("colleague", 10),
                      ("not_applicable", 8)],
        "severity": [("high", 44), ("severe", 26), ("moderate", 24), ("low", 6)],
        "interventions": [("documented", 26), ("submitted_report_to_platforms", 24),
                          ("legal_referrals", 18), ("mental_health_referrals", 16),
                          ("continue_monitoring_the_case", 16)],
        "identities": [("public_figure", 24), ("journalist", 16), ("public_user", 22),
                       ("gender_advocate", 14), ("political_activist", 12),
                       ("educator", 6), ("unknown", 6)],
        "ident_status": [("unknown", 62), ("suspected", 32), ("known", 6)],
        "evidence_prob": 0.66,
        "captions": [
            "Synthetic sexual images generated from public photographs",
            "AI-altered video circulated in a messaging channel",
            "Manipulated images used to discredit the survivor",
        ],
        "summaries": [
            "Sexual images generated from the survivor's publicly available photographs "
            "were circulated in a channel of approximately {n_accounts} members. The "
            "images were technically convincing at small sizes. Removal requests were "
            "filed with {n_posts} hosts.",
            "An AI-altered video depicting the survivor was posted alongside their real "
            "workplace details. The survivor became aware when contacted by a colleague. "
            "The material had been re-shared {n_posts} times before the first report.",
            "Manipulated sexual imagery of the survivor was circulated during a period of "
            "public commentary on {topic}, apparently to discredit them. No uploader "
            "account could be identified.",
        ],
        "impacts": [
            "Reported severe distress at material that cannot be fully removed.",
            "Issued a public statement; reported continued circulation afterwards.",
            "Accepted counselling referral and reduced public activity.",
            "Reported difficulty explaining the material to family members.",
        ],
    },
    {
        "key": "doxxing_identity", "weight": 6,
        "harass": [("doxxing", 40), ("discrimination", 26),
                   ("physical_safety_threats", 18), ("misogynistic_hate_speech", 16)],
        "harass_count": (2, 3),
        "platforms": [("facebook", 40), ("telegram", 24), ("x", 12), ("tiktok", 12),
                      ("website", 12)],
        "relations": [("stranger", 64), ("political_actor", 14), ("colleague", 12),
                      ("not_applicable", 10)],
        "severity": [("high", 40), ("severe", 22), ("moderate", 28), ("low", 10)],
        "interventions": [("documented", 24), ("provided_safety_planning_to_victim", 20),
                          ("submitted_report_to_platforms", 18),
                          ("provided_safety_guideline", 16),
                          ("mental_health_referrals", 12), ("legal_referrals", 10)],
        "interv_count": (3, 4),
        "gender": [("lgbtqia_community", 24), ("transgender", 18), ("lesbian", 14),
                   ("female", 24), ("queer_questioning", 8), ("bisexual", 6),
                   ("gender_diverse_group", 4), ("prefer_not_to_say", 2)],
        "identities": [("gender_advocate", 22), ("human_rights_defender", 16),
                       ("cso_member", 14), ("minority", 14), ("public_user", 16),
                       ("political_activist", 10), ("unknown", 8)],
        "evidence_prob": 0.58,
        "reporters": [("survivor_self", 38), ("partner_organization", 24),
                      ("operator_outreach", 16), ("hotline", 10), ("anonymous", 12)],
        "captions": [
            "Home address published alongside abusive commentary",
            "Survivor outed without consent to family and employer",
            "Personal contact details circulated in a public group",
        ],
        "summaries": [
            "The survivor's home address and workplace were published in a public group "
            "of approximately {n_accounts} members, alongside commentary about their "
            "gender identity. The post was re-shared {n_posts} times before removal.",
            "The survivor was outed without consent to family members and their employer "
            "through messages sent from {n_accounts} accounts over {n_days} days. "
            "Threats followed once the information spread.",
            "Personal contact details were circulated after the survivor spoke publicly "
            "on {topic}. The survivor received calls and messages from unknown numbers "
            "for {n_weeks} weeks afterwards.",
        ],
        "impacts": [
            "Changed phone number and reviewed physical security at home.",
            "Reported estrangement from family members following disclosure.",
            "Took leave from work; accepted counselling referral.",
            "Relocated temporarily; safety plan agreed with the organisation.",
        ],
    },
    {
        "key": "mass_reporting", "weight": 5,
        "harass": [("mass_reporting_to_silence_victims", 56),
                   ("controlling_social_media_accounts", 18),
                   ("misogynistic_hate_speech", 16), ("cyber_bullying", 10)],
        "platforms": [("facebook", 56), ("tiktok", 18), ("instagram", 12),
                      ("youtube", 8), ("x", 6)],
        "relations": [("stranger", 46), ("political_actor", 34),
                      ("authorities_government_officials", 12), ("not_applicable", 8)],
        "severity": [("moderate", 40), ("high", 26), ("low", 24), ("minimal", 10)],
        "interventions": [("page_account_recovery", 26), ("documented", 22),
                          ("submitted_report_to_platforms", 20),
                          ("continue_monitoring_the_case", 18),
                          ("technical_support", 14)],
        "identities": [("gender_advocate", 24), ("political_activist", 22),
                       ("journalist", 18), ("human_rights_defender", 14),
                       ("cso_member", 12), ("critic", 10)],
        "ident_status": [("suspected", 56), ("unknown", 38), ("known", 6)],
        "evidence_prob": 0.44,
        "reporters": [("survivor_self", 40), ("partner_organization", 26),
                      ("operator_outreach", 22), ("unknown", 12)],
        "captions": [
            "Account suspended after coordinated false reports",
            "Repeated takedowns of posts on {topic}",
            "Page restricted following mass reporting of advocacy posts",
        ],
        "summaries": [
            "The survivor's account was suspended following what appeared to be a "
            "coordinated reporting campaign after posts on {topic}. Restoration took "
            "{n_days} days through an appeal. No violation was ultimately found.",
            "Advocacy posts were removed on {n_posts} occasions over {n_weeks} weeks, "
            "each time shortly after publication. The pattern suggests organised false "
            "reporting rather than platform enforcement.",
            "The survivor's page was restricted after a wave of reports from accounts "
            "showing similar creation dates. Reach remained reduced for {n_weeks} weeks "
            "after restoration.",
        ],
        "impacts": [
            "Lost audience reach; reported reduced effectiveness of advocacy work.",
            "Created a backup account and archived content off-platform.",
            "Reported frustration at the absence of platform recourse.",
            "No lasting impact reported once the account was restored.",
        ],
    },
    {
        "key": "security_advisory", "weight": 8,
        "case_type": "technical_support",
        "harass": [("controlling_social_media_accounts", 34), ("cyber_stalking", 24),
                   ("impersonation", 22), ("doxxing", 20)],
        "harass_count": (1, 1),
        "platforms": [("facebook", 40), ("messenger", 18), ("telegram", 16),
                      ("email", 14), ("instagram", 12)],
        "relations": [("not_applicable", 54), ("stranger", 30), ("ex_partner", 10),
                      ("colleague", 6)],
        "severity": [("minimal", 42), ("low", 38), ("moderate", 18), ("high", 2)],
        "interventions": [("provided_digital_security_training", 28), ("2fa_setup", 22),
                          ("password_reset", 16), ("provided_safety_guideline", 16),
                          ("secured_digital_device", 10), ("technical_support", 8)],
        "interv_count": (2, 4),
        "perp_prob": 0.18,
        "evidence_prob": 0.08,
        "pii_prob": 0.44,
        "reporters": [("operator_outreach", 40), ("survivor_self", 26),
                      ("partner_organization", 22), ("hotline", 8), ("unknown", 4)],
        "identities": [("gender_advocate", 20), ("cso_member", 18), ("journalist", 14),
                       ("human_rights_defender", 12), ("educator", 12),
                       ("public_user", 14), ("media_worker", 10)],
        "captions": [
            "Preventive account hardening after a suspicious login",
            "Digital security review requested before a public campaign",
            "Advisory session following a phishing attempt",
        ],
        "summaries": [
            "The survivor requested a security review after receiving a login alert from "
            "an unfamiliar location. No compromise was found. Two-factor authentication "
            "was enabled, {n_accounts} stale app passwords revoked, and recovery contacts "
            "updated.",
            "A preventive digital security session was carried out ahead of a public "
            "campaign on {topic}. Account privacy settings were reviewed and recovery "
            "options confirmed for {n_accounts} accounts.",
            "Following a phishing message imitating a platform notice, the survivor "
            "sought advice. Credentials had not been entered. Passwords were rotated as "
            "a precaution and reporting steps explained.",
        ],
        "impacts": [
            "No harm occurred; preventive measures applied.",
            "Reported increased confidence managing account security.",
            "No lasting impact reported at time of intake.",
            "Requested a follow-up session for colleagues.",
        ],
    },
]

TOPICS = [
    "gender equality", "online safety", "land rights", "labour conditions",
    "domestic violence law", "political participation", "environmental protection",
    "press freedom", "reproductive health", "workplace discrimination",
    "an anti-corruption investigation", "a local election",
]


# ------------------------------------------------------------------------- generation

def get(arch, key):
    return arch.get(key, DEFAULTS[key])


def narrative_vars():
    return {
        "topic": random.choice(TOPICS),
        "n_posts": random.randint(2, 14),
        "n_comments": random.choice([40, 60, 80, 120, 150, 200, 300, 400, 600]),
        "n_accounts": random.choice([3, 5, 8, 12, 20, 30, 45, 60, 90, 120]),
        "n_days": random.randint(2, 21),
        "n_weeks": random.randint(2, 16),
        "n_messages": random.choice([60, 90, 140, 200, 350, 500]),
        "n_years": random.randint(2, 9),
        "amount": random.choice([50, 100, 150, 200, 300, 500, 800, 1000]),
    }


def ident_status_for(arch, relation):
    if "ident_status" in arch:
        return pick(arch["ident_status"])
    if relation in ("ex_partner", "current_partner", "colleague", "manager_supervisor"):
        return pick([("known", 70), ("suspected", 26), ("unknown", 4)])
    return pick([("suspected", 46), ("unknown", 46), ("known", 8)])


def reported_date(today):
    """Recent-weighted, with a bump during the 16 Days of Activism (25 Nov - 10 Dec).

    Intake is not uniform: it grows as the service becomes known, and awareness
    campaigns produce visible spikes. A flat distribution hides both.
    """
    start = today - dt.timedelta(days=WINDOW_DAYS)
    frac = random.random() ** 0.62
    date = start + dt.timedelta(days=int(frac * WINDOW_DAYS))
    if random.random() < 0.11:
        windows = []
        for year in {start.year, today.year, start.year + 1}:
            a = dt.date(year, 11, 25)
            b = dt.date(year, 12, 10)
            if a >= start and b <= today:
                windows.append((a, b))
        if windows:
            a, b = random.choice(windows)
            date = a + dt.timedelta(days=random.randint(0, (b - a).days))
    return date


def status_for_age(age_days, arch_key):
    """Old cases are mostly closed; recent ones are mostly open."""
    if age_days < 45:
        w = [("investigating", 44), ("ongoing", 36), ("referred", 10),
             ("resolved", 8), ("cannot_resolve", 2)]
    elif age_days < 150:
        w = [("ongoing", 30), ("investigating", 22), ("resolved", 24),
             ("referred", 14), ("cannot_resolve", 8), ("rejected", 2)]
    elif age_days < 330:
        w = [("resolved", 38), ("referred", 18), ("cannot_resolve", 18),
             ("ongoing", 14), ("investigating", 6), ("rejected", 6)]
    else:
        w = [("resolved", 46), ("cannot_resolve", 22), ("referred", 16),
             ("ongoing", 8), ("rejected", 6), ("investigating", 2)]
    # Technical support work closes faster and more cleanly than casework.
    if arch_key in ("account_takeover", "security_advisory"):
        w = [(k, v * 2 if k == "resolved" else v) for k, v in w]
    return pick(w)


def ensure_organizations():
    existing = s.api("GET", "/items/organizations?limit=-1&fields=id,name,code") or []
    by_code = {o.get("code"): o["id"] for o in existing}
    created = []
    out = []
    for name, code, weight in ORGANIZATIONS:
        if code in by_code:
            out.append((by_code[code], weight))
            continue
        row = s.api("POST", "/items/organizations",
                    {"name": name, "code": code, "active": True})
        created.append(row["id"])
        out.append((row["id"], weight))
        print(f"  + organization {name} ({code})")
    return out, created


def generate(count):
    org_weighted, created_orgs = ensure_organizations()
    made = {"cases": [], "survivors": [], "perpetrators": [],
            "survivor_pii": [], "perpetrator_pii": [],
            "organizations": created_orgs}

    today = dt.date.today()
    arch_weighted = [(a["key"], a["weight"]) for a in ARCHETYPES]
    by_key = {a["key"]: a for a in ARCHETYPES}
    tally = {}

    for i in range(1, count + 1):
        arch = by_key[pick(arch_weighted)]
        tally[arch["key"]] = tally.get(arch["key"], 0) + 1
        v = narrative_vars()
        variant = random.randrange(len(arch["summaries"]))

        date = reported_date(today)
        age = (today - date).days
        # Drafts are disproportionately recent: an old draft would have been finished.
        draft = random.random() < (0.22 if age < 30 else 0.05)

        survivor = s.api("POST", "/items/survivors", {
            "gender": pick(get(arch, "gender")),
            "identities": m2m("identities_id",
                              pick_many(get(arch, "identities"),
                                        *get(arch, "ident_count")))})
        made["survivors"].append(survivor["id"])

        if random.random() < get(arch, "pii_prob"):
            pii = s.api("POST", "/items/survivor_pii", {
                "survivor": survivor["id"],
                "full_name": f"SYNTHETIC Survivor {i:04d}",
                "contact_phone": f"+855-000-{i:04d}",
                "contact_email": f"synthetic-survivor-{i:04d}@example.invalid",
                "address": f"SYNTHETIC address {i:04d}, not a real location",
                "notes": SYNTHETIC_MARK})
            made["survivor_pii"].append(pii["id"])

        relation = pick(arch["relations"])
        perpetrator = None
        if relation != "not_applicable" and random.random() < get(arch, "perp_prob"):
            status = ident_status_for(arch, relation)
            perpetrator = s.api("POST", "/items/perpetrators", {
                "gender": pick(get(arch, "perp_gender")),
                "identification_status": status,
                "identities": m2m("identities_id",
                                  pick_many(DEFAULTS["identities"], 1, 1))})
            made["perpetrators"].append(perpetrator["id"])
            # Identifying details exist mainly where the perpetrator is actually known.
            p_prob = get(arch, "perp_pii_prob") * (1.8 if status == "known" else 0.5)
            if random.random() < p_prob:
                ppii = s.api("POST", "/items/perpetrator_pii", {
                    "perpetrator": perpetrator["id"],
                    "full_name": f"SYNTHETIC Perpetrator {i:04d}",
                    "known_information": (
                        f"{SYNTHETIC_MARK} Account details recorded at intake."
                        if status == "known" else SYNTHETIC_MARK),
                    "suspected_information": (
                        f"{SYNTHETIC_MARK} Linked to {v['n_accounts']} further accounts."
                        if status != "known" else None),
                    "profile_urls": [{"url": f"https://example.invalid/profile/{i:04d}"}]})
                made["perpetrator_pii"].append(ppii["id"])

        case_type = get(arch, "case_type")
        payload = {
            "case_type": case_type,
            "record_status": "draft" if draft else "submitted",
            "date_reported": date.isoformat(),
            "organization": random.choices([o for o, _ in org_weighted],
                                           weights=[w for _, w in org_weighted],
                                           k=1)[0],
            "case_category": pick([("victim_reported", 66), ("operator_collected", 34)]),
            "reported_by": pick(get(arch, "reporters")),
            "survivor": survivor["id"],
            "perpetrator_relation": relation,
            "contextual_information":
                arch["summaries"][variant].format(**v) + f" {SYNTHETIC_MARK}",
            "comment": random.choice(arch["impacts"]).format(**v),
            "platforms": m2m("platforms_id",
                             pick_many(arch["platforms"], *get(arch, "platform_count"))),
            "harassment_types": m2m("harassment_types_id",
                                    pick_many(arch["harass"], *get(arch, "harass_count"))),
            "interventions": m2m("interventions_id",
                                 pick_many(arch["interventions"],
                                           *get(arch, "interv_count"))),
        }
        if perpetrator:
            payload["perpetrator"] = perpetrator["id"]

        if draft:
            # A draft is genuinely incomplete — that is what makes it a draft.
            if random.random() < 0.5:
                payload["case_status"] = status_for_age(age, arch["key"])
        else:
            payload["case_status"] = status_for_age(age, arch["key"])
            # Technical support always carries a severity; TFGBV cases carry one only
            # where a triage pass has happened.
            if case_type == "technical_support" or random.random() < 0.72:
                payload["severity"] = pick(arch["severity"])

        if random.random() < get(arch, "evidence_prob"):
            payload["evidence_links"] = [
                {"url": f"https://example.invalid/{arch['key']}/{i:04d}-{k}",
                 "captured_at": date.isoformat()}
                for k in range(1, random.randint(1, 3) + 1)]

        case = s.api("POST", "/items/cases", payload)
        made["cases"].append(case["id"])
        if i % 25 == 0:
            print(f"  {i}/{count} cases", flush=True)

    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w") as fh:
        json.dump(made, fh, indent=1)
    return made, tally


def purge():
    try:
        with open(MANIFEST) as fh:
            made = json.load(fh)
    except FileNotFoundError:
        raise SystemExit("no manifest — nothing recorded as generated")
    for coll in ("survivor_pii", "perpetrator_pii", "cases", "survivors",
                 "perpetrators", "organizations"):
        ids = made.get(coll, [])
        if not ids:
            continue
        for i in range(0, len(ids), 50):
            try:
                s.api("DELETE", f"/items/{coll}", ids[i:i + 50])
            except SystemExit:
                pass
        print(f"  deleted {len(ids)} from {coll}")
    os.remove(MANIFEST)


def summarise(tally):
    def agg(path):
        return s.api("GET", path)

    print("\n  archetype mix:")
    for k, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"    {k:28} {n:4}")

    for label, path in (
        ("by record status", "/items/cases?aggregate[count]=id&groupBy=record_status"),
        ("by case type",     "/items/cases?aggregate[count]=id&groupBy=case_type"),
        ("by case status",   "/items/cases?aggregate[count]=id&groupBy=case_status"
                             "&sort=-count.id"),
        ("by severity",      "/items/cases?aggregate[count]=id&groupBy=severity"
                             "&sort=-count.id"),
    ):
        rows = agg(path) or []
        print(f"\n  {label}:")
        for r in rows:
            key = [x for k, x in r.items() if k != "count"][0]
            print(f"    {str(key):28} {r['count']['id']:>4}")

    top = agg("/items/cases_platforms?aggregate[count]=id&groupBy=platforms_id"
              "&sort=-count.id&limit=6") or []
    print("\n  top platforms:")
    for r in top:
        print(f"    {str(r['platforms_id']):28} {r['count']['id']:>4}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=180)
    ap.add_argument("--purge", action="store_true")
    ap.add_argument("--seed", type=int, default=20260904)
    args = ap.parse_args()

    random.seed(args.seed)
    s.login()
    if args.purge:
        purge()
    else:
        made, tally = generate(args.count)
        summarise(tally)
        print(f"\n  manifest: {MANIFEST}")
        print("  remove with: python3 scripts/seed_realistic_data.py --purge")
