import type { Metadata } from "next";
import { LegalShell } from "@/components/legal-shell";

export const metadata: Metadata = {
  title: "Data Processing Addendum — FinCopilot",
  description: "How FinCopilot processes personal data on your behalf (GDPR Art. 28).",
};

export default function DpaPage() {
  return (
    <LegalShell title="Data Processing Addendum" updated="July 13, 2026">
      <p>
        This DPA summary describes how FinCopilot (&quot;Processor&quot;) processes personal data on
        behalf of a customer (&quot;Controller&quot;), consistent with GDPR Article 28. A signable
        DPA is available for business customers on request.
      </p>

      <h2>1. Subject matter &amp; roles</h2>
      <p>
        The Controller determines the purposes of processing; the Processor processes personal data
        only on documented instructions to provide the Service.
      </p>

      <h2>2. Nature &amp; purpose</h2>
      <p>
        Processing consists of storing and analyzing the Controller&apos;s queries and uploaded
        documents to return cited AI research answers within the Controller&apos;s tenant.
      </p>

      <h2>3. Confidentiality &amp; security</h2>
      <ul>
        <li>Personnel are bound to confidentiality.</li>
        <li>Encryption in transit and at rest; role-based, tenant-isolated access; audit logging.</li>
        <li>No use of Controller data to train models.</li>
      </ul>

      <h2>4. Subprocessors</h2>
      <p>
        The Controller authorizes the subprocessors listed on our{" "}
        <a href="/legal/subprocessors">subprocessors page</a>. We impose data-protection obligations
        on each and remain responsible for their performance. We give notice of new subprocessors.
      </p>

      <h2>5. Data subject rights &amp; assistance</h2>
      <p>
        We provide tooling for access, export, and deletion, and reasonably assist the Controller
        with data-subject requests, DPIAs, and breach notification without undue delay.
      </p>

      <h2>6. International transfers</h2>
      <p>
        Where data leaves its region, transfers rely on appropriate safeguards (e.g. Standard
        Contractual Clauses). Subprocessor locations are listed on the subprocessors page.
      </p>

      <h2>7. Return &amp; deletion</h2>
      <p>
        On termination, we delete or return personal data (including derived vectors) within a
        commercially reasonable period, except where retention is legally required.
      </p>

      <h2>8. Contact</h2>
      <p>
        Request a countersigned DPA at{" "}
        <a href="mailto:privacy@fincopilot.app">privacy@fincopilot.app</a>.
      </p>
    </LegalShell>
  );
}
