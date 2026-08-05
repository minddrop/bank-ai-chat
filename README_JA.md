# 邦客大手銀行 AIカスタマーアシスタント（AWS本番アーキテクチャ）

[![Language: English](https://img.shields.io/badge/Language-English-blue.svg)](README.md)
[![Language: 日本語](https://img.shields.io/badge/Language-日本語-red.svg)](README_JA.md)

> **言語切り替え / Language Switch**: [English](README.md) | [日本語 (Japanese)](README_JA.md)

本プロジェクトは、AWS東京リージョン（`ap-northeast-1`）上に構築された、日本の個人向けデジタルバンキング顧客対応用のエンタープライズAIチャットシステムです。Amazon Bedrock (Amazon Nova Lite `amazon.nova-lite-v1:0`)、Amazon OpenSearch ServiceによるRAG検索、およびIn-VPCデュアルコントロールプレーンアーキテクチャを活用しています。

---

## 🌟 主な機能と特徴

1. **銀行員としての高度な敬語・丁寧語対応**
   - 信頼性の高い顧客対応を実現するため、自然で丁寧な日本語敬語（丁寧語・尊敬語・謙譲語）で一貫して応答します。

2. **In-VPC デュアルコントロールプレーン（入力＆出力ガードレール）**
   - **入力ガードレール**: 個人情報保護法（APPI）に基づき、7桁の口座番号、顧客氏名（カタカナ・漢字）、店番号、暗証番号、電話番号等の個人情報（PII）をプロンプト構築前に自動マスキング。プロンプトインジェクション攻撃を防御します。
   - **出力ガードレール**: 検索結果（RAG context）に対するグラウンディングスコアの検証、金融商品取引法・金融庁ガイドラインに基づく個別の投資助言・銘柄推奨の厳格な制限、法的な免責事項の自動付加を行います。

3. **RAGナレッジベース＆コアバンキング合成データ連携**
   - 楽天銀行のFAQデータベース等を活用した実用的なFAQ自動検索エンジン（RAG）を搭載。
   - 勘定系コアバンキング（普通預金、定期預金、外貨預金、直近取引明細）の合成口座データ参照に対応。

4. **FISC安全対策基準準拠のセキュリティ＆改ざん防止監査**
   - AWS KMS (AES-256) 暗号化、S3 Object Lock、およびSHA-256ハッシュ署名付きの改ざん防止監査ログをAWS東京リージョン内に保持。

---

## 📁 ディレクトリ構造

```
bank-ai-chat/
├── GEMINI.md                         # ガバナンス・アーキテクチャ規定・開発ガイドライン
├── README.md                         # 英語版 README（プライマリ）
├── README_JA.md                      # 日本語版 README
├── data/                             # 合成口座データ & FAQデータセット
├── docs/                             # AWSアーキテクチャ・詳細設計書・CI/CD・コスト試算・ADR
│   └── adr/                          # 建築決定記録 (Architectural Decision Records)
├── scripts/                          # FAQクローラー & データベース初期化スクリプト
├── src/                              # バックエンド・コントロールプレーン・勘定系・フロントエンド・LLM・RAG
└── tests/                            # ガードレール・RAG・スキーマ検証用自動テスト
```

---

## 🚀 セットアップと実行方法

### 事前準備
- Python 3.10 以上
- `pytest`（自動テスト実行用）

### インストール＆テスト実行
1. リポジトリのクローンおよび依存関係のインストール:
   ```bash
   pip install -r requirements.txt
   ```
2. 自動テスト・コンプライアンス検証の実行:
   ```bash
   pytest tests/
   ```

---

## ⚖️ 関連規制・セキュリティ基準

- **個人情報保護法 (APPI)**: LLMモデルエンドポイントへの生のPII流出を完全遮断。
- **金融庁 (FSA) AIガイドライン & 金融商品取引法 (FIEA)**: 回答の根拠（Grounding）検証および投資助言行為の禁止。
- **FISC安全対策基準**: 改ざん防止監査ログおよびKMS暗号化の適用。

---

## 📝 ドキュメント運用方針 (Documentation Policy)

[`GEMINI.md`](GEMINI.md) の規定に基づき、**英語 (`README.md`) と日本語 (`README_JA.md`) の2言語によるドキュメント維持管理は README ファイル限定で適用**されます。その他の内部ドキュメントおよびADRは規定の標準言語で管理されます。
