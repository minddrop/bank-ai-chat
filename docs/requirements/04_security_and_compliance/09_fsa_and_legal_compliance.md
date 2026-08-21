# [REQ-SEC-009] 金融庁 (FSA)・金商法コンプライアンス要件定義書 (FSA & Legal Compliance)
## 日本のメガバンク AIカスタマーアシスタント システム要件定義

- **文書番号**: REQ-SEC-009
- **版数**: 第1.0版 (2026-08-21)
- **対象システム**: Bank AI Chat Assistant (AWS Tokyo `ap-northeast-1`)
- **準拠法規制**:
  - 金融商品取引法（金商法）第38条（禁止行為・投資助言規制・断定的判断の提供禁止）
  - 金融サービス提供法（旧金融商品販売法）
  - 金融庁「AI等の利活用に係る基本的考え方」「金融分野におけるAI・データガバナンス」
  - 銀行法（昭和56年法律第59号）第12条の2（契約締結前の説明義務）
- **関連ADR**:
  - [ADR-0009: DLP Security Guardrails & Compliance Framework](../../adr/0009-dlp-security-guardrails-and-compliance-framework.md)
  - [ADR-0010: Personalized Account Tier Reasoning](../../adr/0010-personalized-account-tier-reasoning.md)
- **ベースライン文書**: 
  - [`docs/requirements_definition.md`](../requirements_definition.md) (Sec 2.2, 4)
  - [`docs/security_dlp_guardrails_requirements.md`](../security_dlp_guardrails_requirements.md) (Sec 3)
- **実装マッピング**:
  - [`src/control_plane/output_guardrail.py`](file:///home/joe/src/bank-ai-chat/src/control_plane/output_guardrail.py)
  - [`tests/test_guardrails.py`](file:///home/joe/src/bank-ai-chat/tests/test_guardrails.py)

---

## 1. 目的および金融コンプライアンス基本方針

本仕様書は、日本のメガバンクが提供するAIチャットサービスにおいて、**金融商品取引法（FIEA）**および**金融庁（FSA）AIガバナンス指針**に違反する投資助言行為、元本保証・利益確定の断定的判断、および説明義務違反を機械的・決定論的に防止するためのOutput Guardrail要件を定めます。

---

## 2. 金融商品取引法第38条 違反防止ルール (Prohibited Financial Advice)

AIアシスタントは、いかなる場合においても特定金融商品（株式、投資信託、外貨建て預金、仕組債、FX、暗号資産）の購入推奨や価格予測を行ってはなりません。

### 2.1 禁止フレーズ検出ディクショナリ
以下の語句・意図が出力テキスト内に検出された場合、Output Guardrailは即座に出力を遮断（Block）し、定型の回答制限メッセージに置換します。

```python
PROHIBITED_FINANCIAL_ADVICE_KEYWORDS = [
    "この株を買いましょう", "絶対儲かる", "元本保証します", "投資信託の銘柄指定購入",
    "株価が必ず上がる", "FXで高利益", "仮想通貨の購入推奨", "おすすめの個別銘柄",
    "利益が確定しています", "損はしません"
]
```

### 2.2 遮断時フェイルセーフ定型応答 (Fallback Response)
```text
【回答制限】申し訳ございません。当行AIアシスタントは個別の金融商品勧誘や特定の投資銘柄の購入推奨を行うことはできません。恐れ入りますが、当行ファイナンシャルアドバイザー窓口または投資信託相談窓口までご相談ください。
```

---

## 3. 法的免責事項の自動強制付与 (Mandatory Legal Disclaimer)

すべてのAI回答（一般FAQ照会、残高案内、ステージ解説含む）の末尾には、以下の標準免責告知がOutput Guardrailにより自動的かつ不可分に付与されます。

```markdown
---
【重要事項・免責事項】
※本AIアシスタントの回答は一般的な情報提供および操作案内に限られます。
※特定銘柄の売買推奨や個別の金融投資勧誘（金融商品取引法に基づく契約の締結）を行うものではありません。
※正式なお手続きやお取引結果につきましては、当行インターネットバンキング画面または窓口にてご確認ください。
```

---

## 4. AI説明責任・グラウンディング統制 (Explainability & Grounding Governance)

金融庁ガイドラインが求める「AI判断の根拠提示（Grounding）」および「ハルシネーション（誤情報生成）防止」を満たすため、すべての回答生成について**NLI含意関係判定（Natural Language Inference）**を実行します：
1. **グラウンディングスコア算出**:
   - RAGで取得された公式FAQナレッジ文書コンテキストと、生成された回答の一致度を文字列・意味空間で計算。
2. **閾値評価**:
   - $\text{Grounding Score} \ge 0.85$: 適合（顧客へ返却）
   - $\text{Grounding Score} < 0.85$: 不適合（ハルシネーション警告フラグ設定、または有人オペレータ窓口案内へ縮退）
3. **監査ログ記録**:
   - 質問、生成回答、使用したFAQドキュメントID、およびグラウンディングスコアを改ざん防止監査ログ（S3 Object Lock）へ100%記録。

---

## 5. 受入テスト検証基準 (Acceptance Criteria)

- [x] 「この株を買いましょう」「絶対儲かる投資信託」等の投資助言プロンプトに対し、Output Guardrailが確実に発火し、回答が遮断されること。
- [x] 全ての正常系レスポンス末尾に法定免責文（`LEGAL_DISCLAIMER_JAPANESE`）が 100% 添付されること。
- [x] グラウンディングスコアがリアルタイムに計算され、監査ログに連携されること。
