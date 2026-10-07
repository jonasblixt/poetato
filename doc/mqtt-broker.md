# PoEtato — MQTT broker decision

**DECIDED 2026-09-30: self-hosted broker** (own CA, mTLS). No hosted or public broker. **Broker software: open, likely not Mosquitto** (candidates below).

## Why not hosted (researched 2026-09-30)
- HiveMQ Serverless / EMQX Serverless: username/password only, no client certs → breaks SEC-05/SEC-07 (SE050-held key unused). Shared broker, no SLA.
- Hosted brokers with mTLS are costly for one device: HiveMQ Starter ~$248/mo, EMQX Dedicated Flex ~$234/mo, Cedalo S €39/mo.
- AWS IoT Core (~$1–5/mo, own CA, mTLS) was the only cheap mTLS option. But a wildcard subscription gets no retained messages, which breaks HA discovery unless the device re-announces on `homeassistant/status`. No QoS 2. Vendor lock-in.
- Azure Event Grid MQTT: per its docs, a RETAIN publish fails → poor fit for HA.

## Self-hosted candidates (2026-09-30)
| Broker | Lang / licence | Cert CN → username | TPM key path |
|---|---|---|---|
| EMQX 5.9+ | Erlang, BSL 1.1 (free single node, no clustering; each version → Apache 2 after 4 y) | `peer_cert_as_username = cn` | PEM files only → TLS-terminating proxy |
| FlashMQ | C++, OSL-3.0, Debian repo | Yes since 1.8 (CN as username) | OpenSSL → try transparent tpm2 provider (untested) |
| Mochi MQTT | Go, MIT, library + server | Custom auth hook reading the peer cert | Native: Go `crypto.Signer` backed by the TPM |
| NATS (MQTT listener) | Go, Apache 2 | TLS cert → user mapping | Config-file keys; proxy |
| HiveMQ CE | Java, Apache 2 | Must write an extension (no built-in auth) | Unclear |
| VerneMQ | Erlang, Apache 2 source, binaries under EULA | `use_identity_as_username` | Proxy |
| RabbitMQ MQTT | Erlang, MPL | `ssl_cert_login_from = common_name` | Proxy. ✗ Retained messages not delivered on wildcard subs (breaks HA discovery), no QoS 2 |

## Broker requirements
- TLS 1.2+ only (1.3 preferred), ECDHE + AEAD, client certificate required, cert CN used as username.
- Client certs issued by the offline PoEtato CA (subject from the MCX N unique ID). Home Assistant gets its own client cert.
- Per-identity ACL: each device may only use its own topic tree + HA discovery/status. Command topics are writable only by HA.
- CRL for revocation.
- No anonymous access, no plaintext listener (except isolated bench setups).
- Retained messages must reach wildcard subscribers (HA discovery).
- Optional later: a bridge to a cloud broker for remote access. The local broker stays primary so door control and monitoring survive an internet outage.

## Broker key in TPM (plan, 2026-09-30, untested)
The server-side counterpart of the SE050: the broker's TLS key is generated in the host TPM 2.0 and never leaves it. The CSR is signed by the offline CA.
- Key: ECC P-256 via tpm2-openssl (OpenSSL 3 provider). Stored as a `TSS2 PRIVATE KEY` PEM blob wrapped by the TPM, so it is useless on other hardware.
- CSR: generated with `openssl req -provider tpm2 -provider default`; the CA verifies the CSR signature.
- Offline CA sets the SAN/EKU (serverAuth) from its own extension file, not from the CSR.
- Separate issuing CAs under the offline root: **server CA** (broker) and **device CA** (PoEtato + HA client certs). The broker trusts only the device CA for clients; the device trust store = server CA (or the root).
- Ways to use the key:
  - OpenSSL-based broker: activate the tpm2 provider via `OPENSSL_CONF`, keyfile = TSS2 PEM. Test first.
  - Go broker: TPM-backed `crypto.Signer`.
  - Any broker: HAProxy (or similar) terminates TLS with the TPM key and passes the client cert CN via PROXY v2 (`send-proxy-v2-ssl-cn`), if the broker can take the identity from it.
- Ops: the broker process needs `/dev/tpmrm0` (tss group; device passthrough if in an LXC). A TPM clear, board swap or restore to new hardware means a new key → new CSR → re-sign. Document as a procedure. Root on the host can *use* the key but not copy it.

## Firmware to-dos (app/)
- Add a client cert + SE050-backed key to the TLS sec_tag list; today `mqtt_client.c` registers only a CA.
- Enable ECDHE-ECDSA-AES-GCM suites; `prj.conf` currently enables only ECDHE_RSA_AES128_GCM_SHA256. Required for a P-256 broker key.
- Stable client ID from the unique ID (currently random per boot).
- Subscribe to `homeassistant/status` and re-publish discovery on `online`; retained discovery configs; LWT for availability.
