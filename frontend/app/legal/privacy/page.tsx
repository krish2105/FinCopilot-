import type { Metadata } from "next";
import { LegalShell } from "@/components/legal-shell";

export const metadata: Metadata = {
  title: "Privacy Policy — FinCopilot",
  description: "How FinCopilot collects, uses, and protects your data.",
};

export default function PrivacyPage() {
  return (
    <LegalShell title="Privacy Policy" updated="July 13, 2026">
      <p>
        This policy explains what data FinCopilot collects, how we use it, and your rights. We follow
        GDPR-style principles regardless of where you are.
      </p>

      <h2>1. Data we process</h2>
      <ul>
        <li>
          <strong>Account data</strong> — email and authentication identifiers.
        </li>
        <li>
          <strong>Usage data</strong> — queries you submit, documents you upload to your private data
          rooms, and interaction logs used to operate and secure the Service.
        </li>
        <li>
          <strong>Technical data</strong> — IP, device/browser, and diagnostic logs.
        </li>
      </ul>

      <h2>2. Your data is not used to train models</h2>
      <p>
        <strong>
          We do not use your queries or uploaded documents to train AI models, and we send them to
          model providers only under no-training / zero-retention terms where offered.
        </strong>{" "}
        Your private data rooms are tenant-isolated and never used to answer another customer&apos;s
        questions.
      </p>

      <h2>3. How we use data</h2>
      <ul>
        <li>To provide, secure, and improve the Service.</li>
        <li>To enforce quotas and prevent abuse.</li>
        <li>To meet legal obligations.</li>
      </ul>

      <h2>4. Sharing &amp; subprocessors</h2>
      <p>
        We share data only with the infrastructure and AI subprocessors needed to run the Service,
        listed on our <a href="/legal/subprocessors">subprocessors page</a>. We do not sell personal
        data.
      </p>

      <h2>5. Security</h2>
      <p>
        Data is encrypted in transit (TLS) and at rest. Access is role-based, tenant-isolated, and
        audit-logged. Prompt-injection defenses treat retrieved/uploaded content as untrusted.
      </p>

      <h2>6. Your rights</h2>
      <p>
        You can export or permanently delete your data (including your vectors) from within the
        product, or by contacting us. You may access, correct, or restrict processing of your data.
      </p>

      <h2>7. Contact</h2>
      <p>
        Data requests: <a href="mailto:privacy@fincopilot.app">privacy@fincopilot.app</a>.
      </p>
    </LegalShell>
  );
}
