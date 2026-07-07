# Data Model

The backend is a single service with a single database, but the data is not a flat pile of
tables — it falls into a handful of **domains** with clear boundaries and a clear sense of
ownership. This page maps those domains, shows which entity owns which, and makes the
ownership rules legible from the schema itself. It complements the
[Persistence Layer](/architecture/backend/persistence), which covers the mechanics
(SQLAlchemy, repositories, migrations); here we care about the *shape* of the data and the
relationships between entities.

Every table shares the same base: a 12-character nanoid primary key (`id`) and UTC
`created_at` / `updated_at` timestamps. Those are covered in the persistence guide and
omitted from the diagrams below so the relationships stand out.

## 1. Ownership is written in the delete rules

The most useful thing to know about this schema is that **every foreign key declares what
happens when its target is deleted**, and that single choice tells you the nature of the
relationship. There are three, and learning to read them makes the rest of the model
obvious.

<Figure tag="Figure 1" title="The three relationships, read from the delete rule" id="fig-ownership-legend">
<svg viewBox="0 0 780 300" role="img" aria-label="Ownership relationship legend" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="tbm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/>
    </marker>
    <marker id="tbm-ah-data" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-data)"/>
    </marker>
    <marker id="tbm-ah-accent" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-accent)"/>
    </marker>
  </defs>
  <!-- owns -->
  <g font-size="12" text-anchor="middle">
    <rect x="30" y="34" width="120" height="38" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="90" y="58" fill="var(--tbm-dgm-ink)">Character</text>
    <rect x="270" y="34" width="120" height="38" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="330" y="58" fill="var(--tbm-dgm-ink)">Chat</text>
  </g>
  <line x1="150" y1="53" x2="266" y2="53" stroke="var(--tbm-dgm-data)" stroke-width="2.4" marker-end="url(#tbm-ah-data)"/>
  <text x="210" y="44" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-data)">owns</text>
  <text x="410" y="49" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Composition · ON DELETE CASCADE</text>
  <text x="410" y="67" font-size="11.5" fill="var(--tbm-dgm-ink-2)">Delete the owner and its parts go with it. The part cannot outlive the whole.</text>
  <!-- references -->
  <g font-size="12" text-anchor="middle">
    <rect x="30" y="128" width="120" height="38" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="90" y="152" fill="var(--tbm-dgm-ink)">Chat</text>
    <rect x="270" y="128" width="120" height="38" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="330" y="152" fill="var(--tbm-dgm-ink)">Model</text>
  </g>
  <line x1="150" y1="147" x2="266" y2="147" stroke="var(--tbm-dgm-arrow)" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#tbm-ah)"/>
  <text x="210" y="138" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-ink-2)">refs</text>
  <text x="410" y="143" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Reference · ON DELETE SET NULL</text>
  <text x="410" y="161" font-size="11.5" fill="var(--tbm-dgm-ink-2)">Delete the target and the link is cleared; the referrer survives with a gap.</text>
  <!-- protected -->
  <g font-size="12" text-anchor="middle">
    <rect x="30" y="222" width="120" height="38" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="90" y="246" fill="var(--tbm-dgm-ink)">Model</text>
    <rect x="270" y="222" width="120" height="38" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="330" y="246" fill="var(--tbm-dgm-ink)">ModelFamily</text>
  </g>
  <line x1="150" y1="241" x2="266" y2="241" stroke="var(--tbm-dgm-accent)" stroke-width="2.4" marker-end="url(#tbm-ah-accent)"/>
  <text x="208" y="232" text-anchor="middle" font-size="11" font-weight="700" fill="var(--tbm-dgm-accent)">needs</text>
  <text x="410" y="237" font-size="12.5" font-weight="700" fill="var(--tbm-dgm-ink)">Protected reference · ON DELETE RESTRICT</text>
  <text x="410" y="255" font-size="11.5" fill="var(--tbm-dgm-ink-2)">The target can't be deleted while anything still points at it.</text>
</svg>
<template #caption>

**Read every arrow as a delete rule.** A solid green arrow is *ownership* — deleting the
source cascades to the target (`ON DELETE CASCADE`). A dashed arrow is a *reference* —
deleting the target only nulls the link (`ON DELETE SET NULL`), so a chat keeps working
after its model is deleted. A solid amber arrow is a *protected reference* — the target is
shared infrastructure and cannot be deleted while anything still depends on it
(`ON DELETE RESTRICT`). These three styles are used throughout the diagrams below.

</template>
</Figure>

This is why a chat can lose its model, template, preset, or persona and still open: those
are references, and the chat also keeps **name snapshots** so the history stays legible
even after the referenced record is gone. It is also why deleting a character wipes its
chats, messages, and lorebooks in one go: the character *owns* them.

## 2. The domain map

Grouping the entities by what they're about yields six domains plus a passive observability
sink. Even though this is one monolith with one database, these boundaries are real — code
is organized into matching [vertical slices](/architecture/backend/project-structure), and
cross-domain links are almost always *references* (dashed), not ownership. Ownership chains
stay **inside** a domain; the arrows that cross a boundary are the loans one domain takes
from another.

<Figure tag="Figure 2" title="Entities grouped into domains, with cross-domain links" id="fig-domain-map">
<svg viewBox="0 0 960 615" role="img" aria-label="Data model domain map" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="dm-ah" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/></marker>
    <marker id="dm-ah-data" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-data)"/></marker>
    <marker id="dm-ah-accent" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-accent)"/></marker>
  </defs>
  <g stroke-dasharray="5 4">
    <rect x="24" y="48" width="264" height="196" rx="12" fill="var(--tbm-dgm-accent-soft)" stroke="var(--tbm-dgm-accent)" stroke-opacity=".6"/>
    <rect x="348" y="48" width="264" height="196" rx="12" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)" stroke-opacity=".6"/>
    <rect x="672" y="48" width="264" height="196" rx="12" fill="var(--tbm-dgm-provider-soft)" stroke="var(--tbm-dgm-provider)" stroke-opacity=".6"/>
    <rect x="24" y="284" width="264" height="138" rx="12" fill="var(--tbm-dgm-data-soft)" stroke="var(--tbm-dgm-data)" stroke-opacity=".6"/>
    <rect x="348" y="284" width="264" height="138" rx="12" fill="var(--tbm-dgm-brand-soft)" stroke="var(--tbm-dgm-brand)" stroke-opacity=".6"/>
    <rect x="672" y="284" width="264" height="312" rx="12" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)" stroke-opacity=".6"/>
    <rect x="24" y="462" width="588" height="80" rx="12" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  </g>
  <g font-size="11.5" font-weight="700" letter-spacing=".04em">
    <text x="40" y="70" fill="var(--tbm-dgm-accent)">CHARACTERS &amp; PERSONAS</text>
    <text x="364" y="70" fill="var(--tbm-dgm-backend)">CONVERSATIONS</text>
    <text x="688" y="70" fill="var(--tbm-dgm-provider)">PROVIDERS &amp; MODELS</text>
    <text x="40" y="306" fill="var(--tbm-dgm-data)">WORLD &amp; LORE</text>
    <text x="364" y="306" fill="var(--tbm-dgm-brand)">KNOWLEDGE &amp; RAG</text>
    <text x="688" y="306" fill="var(--tbm-dgm-frontend)">PROMPT BUILDING</text>
    <text x="40" y="484" fill="var(--tbm-dgm-faint)">OBSERVABILITY · write-only sink</text>
  </g>
  <g fill="none">
    <line x1="480" y1="116" x2="480" y2="138" stroke="var(--tbm-dgm-data)" stroke-width="2.2" marker-end="url(#dm-ah-data)"/>
    <line x1="480" y1="174" x2="480" y2="196" stroke="var(--tbm-dgm-data)" stroke-width="2.2" marker-end="url(#dm-ah-data)"/>
    <line x1="804" y1="116" x2="804" y2="138" stroke="var(--tbm-dgm-data)" stroke-width="2.2" marker-end="url(#dm-ah-data)"/>
    <line x1="804" y1="174" x2="804" y2="196" stroke="var(--tbm-dgm-accent)" stroke-width="2.2" marker-end="url(#dm-ah-accent)"/>
    <line x1="156" y1="352" x2="156" y2="374" stroke="var(--tbm-dgm-data)" stroke-width="2.2" marker-end="url(#dm-ah-data)"/>
    <line x1="804" y1="352" x2="804" y2="374" stroke="var(--tbm-dgm-data)" stroke-width="2.2" marker-end="url(#dm-ah-data)"/>
    <line x1="804" y1="432" x2="804" y2="410" stroke="var(--tbm-dgm-data)" stroke-width="2.2" marker-end="url(#dm-ah-data)"/>
    <line x1="480" y1="374" x2="480" y2="352" stroke="var(--tbm-dgm-faint)" stroke-width="1.6" stroke-dasharray="2 3" marker-end="url(#dm-ah)"/>
    <line x1="240" y1="98" x2="394" y2="98" stroke="var(--tbm-dgm-data)" stroke-width="2.2" marker-end="url(#dm-ah-data)"/>
    <path d="M240 110 H306 V334 H242" stroke="var(--tbm-dgm-data)" stroke-width="2.2" marker-end="url(#dm-ah-data)"/>
    <line x1="540" y1="316" x2="540" y2="240" stroke="var(--tbm-dgm-data)" stroke-width="2.2" marker-end="url(#dm-ah-data)"/>
    <path d="M396 110 H318 V156 H242" stroke="var(--tbm-dgm-arrow)" stroke-width="1.8" stroke-dasharray="6 4" marker-end="url(#dm-ah)"/>
    <path d="M564 98 H642 V156 H718" stroke="var(--tbm-dgm-arrow)" stroke-width="1.8" stroke-dasharray="6 4" marker-end="url(#dm-ah)"/>
    <path d="M564 110 H654 V334 H718" stroke="var(--tbm-dgm-arrow)" stroke-width="1.8" stroke-dasharray="6 4" marker-end="url(#dm-ah)"/>
    <path d="M888 156 H910 V334 H890" stroke="var(--tbm-dgm-arrow)" stroke-width="1.6" stroke-dasharray="6 4" marker-end="url(#dm-ah)"/>
  </g>
  <g font-size="12" text-anchor="middle">
    <rect x="72" y="80" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="156" y="103" fill="var(--tbm-dgm-ink)">Character</text>
    <rect x="72" y="138" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="156" y="161" fill="var(--tbm-dgm-ink)">Persona</text>
    <rect x="396" y="80" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-backend)" stroke-width="1.8"/><text x="480" y="103" font-weight="700" fill="var(--tbm-dgm-ink)">Chat</text>
    <rect x="396" y="138" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="480" y="161" fill="var(--tbm-dgm-ink)">Message</text>
    <rect x="396" y="196" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="480" y="219" fill="var(--tbm-dgm-ink)">MessageAlternative</text>
    <rect x="720" y="80" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="804" y="103" fill="var(--tbm-dgm-ink)">Provider</text>
    <rect x="720" y="138" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="804" y="161" fill="var(--tbm-dgm-ink)">Model</text>
    <rect x="720" y="196" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="804" y="219" fill="var(--tbm-dgm-ink)">ModelFamily</text>
    <rect x="72" y="316" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="156" y="339" fill="var(--tbm-dgm-ink)">Lorebook</text>
    <rect x="72" y="374" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="156" y="397" fill="var(--tbm-dgm-ink)">LoreEntry</text>
    <rect x="396" y="316" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="480" y="339" fill="var(--tbm-dgm-ink)">DataBankEntry</text>
    <rect x="396" y="374" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="480" y="397" fill="var(--tbm-dgm-ink)">Embedding</text>
    <rect x="720" y="316" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="804" y="339" fill="var(--tbm-dgm-ink)">PromptTemplate</text>
    <rect x="720" y="374" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="804" y="397" fill="var(--tbm-dgm-ink)">TemplateFragment</text>
    <rect x="720" y="432" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="804" y="455" fill="var(--tbm-dgm-ink)">PromptFragment</text>
    <rect x="720" y="490" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="804" y="513" fill="var(--tbm-dgm-ink)">Preset</text>
    <rect x="720" y="548" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="804" y="571" fill="var(--tbm-dgm-ink)">Profile</text>
    <rect x="48" y="494" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="132" y="517" fill="var(--tbm-dgm-ink)">LlmAuditLog</text>
    <rect x="236" y="494" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="320" y="517" fill="var(--tbm-dgm-ink)">HttpLog</text>
    <rect x="424" y="494" width="168" height="36" rx="8" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/><text x="508" y="517" fill="var(--tbm-dgm-ink)">ErrorLog</text>
  </g>
  <g text-anchor="middle">
    <text x="317" y="90" font-size="10.5" font-weight="700" fill="var(--tbm-dgm-data)">owns</text>
    <text x="330" y="266" font-size="10.5" font-weight="700" fill="var(--tbm-dgm-data)">owns</text>
    <rect x="460" y="255" width="112" height="15" rx="3" fill="var(--tbm-dgm-surface-2)"/>
    <text x="516" y="266" font-size="10.5" font-weight="700" fill="var(--tbm-dgm-data)">scoped to (owned by)</text>
    <rect x="244" y="139" width="70" height="14" rx="3" fill="var(--tbm-dgm-surface-2)"/>
    <text x="279" y="150" font-size="10.5" fill="var(--tbm-dgm-ink-2)">refs persona</text>
    <text x="602" y="90" font-size="10.5" fill="var(--tbm-dgm-ink-2)">refs model</text>
    <rect x="598" y="245" width="122" height="15" rx="3" fill="var(--tbm-dgm-surface-2)"/>
    <text x="659" y="256" font-size="10.5" fill="var(--tbm-dgm-ink-2)">refs template · preset</text>
    <text x="916" y="256" text-anchor="start" font-size="10" fill="var(--tbm-dgm-ink-2)">refs</text>
    <text x="826" y="188" font-size="10" fill="var(--tbm-dgm-accent)">needs</text>
    <text x="522" y="366" font-size="9.5" fill="var(--tbm-dgm-faint)">indexes</text>
  </g>
</svg>
<template #caption>

**Ownership stays home; loans cross the line.** Inside each domain, ownership chains run
top to bottom (green): a `Character` owns its `Chat`s, a `Chat` owns its `Message`s and
each `Message` its alternatives; a `Lorebook` owns its `LoreEntry`s; a `Provider` owns its
`Model`s; a `PromptTemplate` and a `PromptFragment` jointly own the `TemplateFragment` rows
that join them. The dashed arrows that cross a boundary are all references — a `Chat`
*borrows* a model, template, preset, and persona but owns none of them. `Model` *needs*
its `ModelFamily` (amber, protected). `Profile` is the odd one out: it owns nothing and is
owned by nothing — it is a pure bundle of four references (see §4). Observability is a
write-only sink nothing else points at.

</template>
</Figure>

## 3. The Chat aggregate

`Chat` is the busiest entity in the schema and the one worth understanding in detail,
because it is where a roleplay session is assembled at generation time. It sits at the
center of one ownership relationship, four references, and a couple of provenance
snapshots.

<Figure tag="Figure 3" title="Everything a Chat pulls together" id="fig-chat-aggregate">
<svg viewBox="0 0 820 540" role="img" aria-label="The Chat aggregate" style="font-family:var(--vp-font-family-base)">
  <defs>
    <marker id="ca-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-arrow)"/></marker>
    <marker id="ca-ah-data" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="var(--tbm-dgm-data)"/></marker>
  </defs>
  <!-- owner -->
  <rect x="330" y="24" width="160" height="42" rx="9" fill="var(--tbm-dgm-accent-soft)" stroke="var(--tbm-dgm-accent)"/>
  <text x="410" y="45" text-anchor="middle" font-size="13" font-weight="700" fill="var(--tbm-dgm-ink)">Character</text>
  <text x="410" y="59" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">the owner</text>
  <!-- chat -->
  <rect x="305" y="118" width="210" height="58" rx="10" fill="var(--tbm-dgm-backend-soft)" stroke="var(--tbm-dgm-backend)" stroke-width="1.6"/>
  <text x="410" y="143" text-anchor="middle" font-size="14" font-weight="700" fill="var(--tbm-dgm-ink)">Chat</text>
  <text x="410" y="161" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">the session</text>
  <!-- owned messages -->
  <rect x="330" y="228" width="160" height="38" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="410" y="252" text-anchor="middle" font-size="12.5" fill="var(--tbm-dgm-ink)">Message</text>
  <rect x="305" y="300" width="210" height="38" rx="9" fill="var(--tbm-dgm-surface)" stroke="var(--tbm-dgm-border-strong)"/>
  <text x="410" y="324" text-anchor="middle" font-size="12.5" fill="var(--tbm-dgm-ink)">MessageAlternative (swipes)</text>
  <!-- references left -->
  <rect x="40" y="112" width="150" height="34" rx="8" fill="var(--tbm-dgm-provider-soft)" stroke="var(--tbm-dgm-provider)"/>
  <text x="115" y="134" text-anchor="middle" font-size="12" fill="var(--tbm-dgm-ink)">Model</text>
  <rect x="40" y="160" width="150" height="34" rx="8" fill="var(--tbm-dgm-accent-soft)" stroke="var(--tbm-dgm-accent)"/>
  <text x="115" y="182" text-anchor="middle" font-size="12" fill="var(--tbm-dgm-ink)">Persona</text>
  <!-- references right -->
  <rect x="630" y="112" width="150" height="34" rx="8" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
  <text x="705" y="134" text-anchor="middle" font-size="12" fill="var(--tbm-dgm-ink)">PromptTemplate</text>
  <rect x="630" y="160" width="150" height="34" rx="8" fill="var(--tbm-dgm-frontend-soft)" stroke="var(--tbm-dgm-frontend)"/>
  <text x="705" y="182" text-anchor="middle" font-size="12" fill="var(--tbm-dgm-ink)">Preset</text>
  <!-- provenance -->
  <rect x="255" y="392" width="310" height="56" rx="10" fill="var(--tbm-dgm-surface-2)" stroke="var(--tbm-dgm-border)"/>
  <text x="410" y="414" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--tbm-dgm-ink)">Provenance snapshots (plain strings, not FKs)</text>
  <text x="410" y="432" text-anchor="middle" font-size="10.5" fill="var(--tbm-dgm-ink-2)">initial_profile_name · last_profile_name · model_name</text>
  <!-- owns arrows (green) -->
  <line x1="410" y1="66" x2="410" y2="116" stroke="var(--tbm-dgm-data)" stroke-width="2.4" marker-end="url(#ca-ah-data)"/>
  <text x="424" y="94" font-size="10.5" font-weight="700" fill="var(--tbm-dgm-data)">owns</text>
  <line x1="410" y1="176" x2="410" y2="226" stroke="var(--tbm-dgm-data)" stroke-width="2.4" marker-end="url(#ca-ah-data)"/>
  <text x="424" y="204" font-size="10.5" font-weight="700" fill="var(--tbm-dgm-data)">owns</text>
  <line x1="410" y1="266" x2="410" y2="298" stroke="var(--tbm-dgm-data)" stroke-width="2.4" marker-end="url(#ca-ah-data)"/>
  <text x="424" y="288" font-size="10.5" font-weight="700" fill="var(--tbm-dgm-data)">owns</text>
  <!-- ref arrows (dashed) -->
  <g fill="none" stroke="var(--tbm-dgm-arrow)" stroke-width="1.8" stroke-dasharray="6 4">
    <path d="M305 147 H250 V129 H192" marker-end="url(#ca-ah)"/>
    <path d="M305 147 H250 V177 H192" marker-end="url(#ca-ah)"/>
    <path d="M515 147 H570 V129 H628" marker-end="url(#ca-ah)"/>
    <path d="M515 147 H570 V177 H628" marker-end="url(#ca-ah)"/>
  </g>
  <text x="410" y="14" text-anchor="middle" font-size="10" fill="var(--tbm-dgm-ink-2)">— dashed = reference (SET NULL) —</text>
  <line x1="410" y1="338" x2="410" y2="390" stroke="var(--tbm-dgm-faint)" stroke-width="1.4" stroke-dasharray="2 3"/>
</svg>
<template #caption>

**One owner, four loans, three snapshots.** A `Chat` belongs to exactly one `Character`
(delete the character and the chat cascades away) and owns its `Message`s, each of which
owns its swipe `MessageAlternative`s. Everything else it touches is a *reference*: the
`Model`, `Persona`, `PromptTemplate`, and `Preset` are all nullable and set-null on delete,
so a chat degrades gracefully rather than breaking. To keep history readable even after a
referenced record is gone, the chat also stores plain-string **snapshots** —
`model_name` and the profile names it was created with and last had applied.

</template>
</Figure>

Applying a **profile** (a loadout) to a chat — via `POST /api/chats/{id}/profile` — simply
copies that profile's four references onto the chat and records its name in
`last_profile_name`. The profile itself is never linked; only its values are copied. This
is why profiles can be edited or deleted freely without disturbing any chat that once used
one.

## 4. Domain reference

The six domains and their entities, with the columns that carry the relationships. Full
column definitions live in the ORM models under
[`core/persistence/models/`](https://github.com/delfianto/the-bannered-mare/tree/main/backend/src/core/persistence/models).

### Characters & Personas

| Entity | Table | Owns | References | Notes |
|--------|-------|------|-----------|-------|
| `Character` | `characters` | `Chat`, `Lorebook`, scoped `DataBankEntry` | — | The NPC the LLM plays. Rich card fields (personality, scenario, greetings, example dialogues), plus `gender` (enum) and free-text card metadata. |
| `Persona` | `personas` | — | — | The user's own role. `is_default` picks the one applied to new chats. Referenced by `Chat` and `Profile`. |

### Conversations

| Entity | Table | Owns | References | Notes |
|--------|-------|------|-----------|-------|
| `Chat` | `chats` | `Message` | `Character` (owner), `Model`, `PromptTemplate`, `Persona`, `Preset` | The session. See [§3](#_3-the-chat-aggregate). Carries `model_name` / profile-name snapshots. |
| `Message` | `messages` | `MessageAlternative` | `Chat` (owner) | `role` (enum: user/assistant/system), `content`, cached `token_count`, optional `reasoning_content`, and `active_index` picking the live swipe. |
| `MessageAlternative` | `message_alternatives` | — | `Message` (owner) | A regenerated "swipe". Ordered by `ordinal`. |

### World & Lore

| Entity | Table | Owns | References | Notes |
|--------|-------|------|-----------|-------|
| `Lorebook` | `lorebooks` | `LoreEntry` | `Character` (owner, **nullable**) | A null `character_id` with `is_global = true` makes it apply to every chat. |
| `LoreEntry` | `lore_entries` | — | `Lorebook` (owner) | A keyword-triggered fact. Rich activation controls: primary/secondary `keys`, `secondary_logic` (enum), `position` (enum), `depth`, `priority`, regex/whole-word/case toggles. |

### Providers & Models

| Entity | Table | Owns | References | Notes |
|--------|-------|------|-----------|-------|
| `Provider` | `providers` | `Model` | — | An API connection. `provider_type` (enum: openai, anthropic, google, openrouter, xai, ollama, lmstudio, custom); API keys live in env vars, never the DB. |
| `Model` | `models` | — | `Provider` (owner), `ModelFamily` (**protected**), `PromptTemplate` | A usable model config. Optional OpenRouter routing; free-form `parameters` JSON. |
| `ModelFamily` | `model_families` | — | — | Shared capability/parameter schema for a family of models. **Protected**: cannot be deleted while any `Model` uses it. |

### Prompt Building

| Entity | Table | Owns | References | Notes |
|--------|-------|------|-----------|-------|
| `PromptTemplate` | `prompt_templates` | `TemplateFragment` | — | Component `component_order` + `components_enabled` map + a Jinja2 `system_template`. Referenced by `Chat`, `Model`, `Profile`. |
| `PromptFragment` | `prompt_fragments` | `TemplateFragment` | — | A reusable Jinja2 block (`fragment_type`: system/nsfw/jailbreak/instruction/context). `is_global` fragments are available to every template. |
| `TemplateFragment` | `template_fragments` | — | `PromptTemplate` (owner), `PromptFragment` (owner) | The **many-to-many join** carrying `position`, `ordinal`, `depth`. Owned by *both* ends. |
| `Preset` | `presets` | — | — | A named sampling-parameter set (`parameters` JSON). Referenced by `Chat`, `Profile`. |
| `Profile` | `profiles` | — | `PromptTemplate`, `Preset`, `Persona`, `Model` (all references) | A loadout — a selectable bundle applied to a chat. Owns nothing; `source` / `source_filename` record where an imported one came from. |

### Knowledge & RAG

| Entity | Table | Owns | References | Notes |
|--------|-------|------|-----------|-------|
| `DataBankEntry` | `data_bank_entries` | — | `Character` (owner) or `Chat` (owner) | User-managed knowledge. `scope` (global/character/chat) decides which owner (if any) it hangs off. |
| `Embedding` | `embeddings` | — | *(none — see §5)* | A `Vector(768)` chunk with a **polymorphic** `source_type` + `source_id` pointer and a `content_hash` for dedup. |

### Observability

`LlmAuditLog`, `HttpLog`, and `ErrorLog` are a write-only audit sink — one row per LLM
call, HTTP request, and unhandled error respectively. `LlmAuditLog` keeps a `chat_id`
*reference* (set-null, so audit rows survive their chat); the other two hold no foreign
keys. They are written by middleware and the audit writer and read only through the
[admin log endpoints](/api/system).

## 5. Two entities that break the rules on purpose

Most of the schema follows the ownership rules above, but two entities deliberately don't,
and both are worth understanding.

**`Embedding` has no foreign keys.** It is a *derived index*, not a domain entity: a vector
plus a `source_type` (`message` or `data_bank`) and a `source_id` that points at whatever
it was generated from. Because the pointer is polymorphic it can't be a database FK, so
integrity is maintained in the service layer instead — deleting a data-bank entry purges
its embeddings; a `content_hash` prevents re-embedding unchanged text. Treating embeddings
as a rebuildable cache rather than owned data is what lets the RAG index be dropped and
regenerated without touching the source records. The vector dimension is pinned at 768 to
match the embedding model, because the VectorChord index requires a fixed-dimension column.

**The audit logs are a sink, not a graph.** They accumulate a record of what happened and
are never referenced by anything else. The one link they keep — `LlmAuditLog.chat_id` — is
a set-null reference precisely so that deleting a chat never deletes the audit trail of the
calls it made.

## Related reading

- [Persistence Layer](/architecture/backend/persistence) — how these entities are stored,
  queried, and migrated (base model, repositories, async/sync split, Alembic).
- [Project Structure](/architecture/backend/project-structure) — the vertical slices that
  own each domain's code.
- [API Reference](/api/) — the endpoints that create, read, and mutate these
  entities.
