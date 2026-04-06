from __future__ import annotations
"""
Peer service — manages P2P node discovery, registration, and health.
"""
import socket
from datetime import datetime, timezone

import requests as http_requests
from flask import current_app

from app import db
from app.models.peer import Peer
from app.utils.logger import logger


class PeerService:
    """Handles peer lifecycle: registration, heartbeat, broadcasting."""

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @staticmethod
    def register_peer(ip_address: str, port: int, hostname: str | None = None) -> Peer:
        """
        Add or update a peer record. Returns the Peer instance.
        If the peer already exists (same ip+port), it is touched (last_seen updated).
        """
        peer = db.session.query(Peer).filter_by(
            ip_address=ip_address, port=port
        ).first()

        if peer:
            peer.touch()
            if hostname:
                peer.hostname = hostname
        else:
            peer = Peer(
                ip_address=ip_address,
                port=port,
                hostname=hostname or ip_address,
                last_seen=datetime.now(timezone.utc),
                status="active",
            )
            db.session.add(peer)

        db.session.commit()
        logger.info("Peer registered/updated: %s:%d", ip_address, port)
        return peer

    @staticmethod
    def get_active_peers() -> list[Peer]:
        """Return all peers with status='active'."""
        return db.session.query(Peer).filter_by(status="active").all()

    # ------------------------------------------------------------------
    # Bootstrap: announce THIS node to a remote peer
    # ------------------------------------------------------------------

    @staticmethod
    def announce_to_peer(peer_base_url: str) -> bool:
        """
        Send a POST /api/p2p/peers/register to the target peer,
        telling it about this node.

        Returns True on success, False on failure.
        """
        import json
        from app.utils.hmac_auth import sign_p2p_request

        my_ip   = current_app.config.get("NODE_IP", "127.0.0.1")
        my_port = current_app.config.get("NODE_PORT", 5000)
        my_host = socket.gethostname()

        payload = json.dumps({
            "ip_address": my_ip,
            "port":       my_port,
            "hostname":   my_host,
        }).encode("utf-8")

        path    = "/api/p2p/peers/register"
        headers = {
            "Content-Type": "application/json",
            **sign_p2p_request("POST", path, payload),
        }

        try:
            resp = http_requests.post(
                f"{peer_base_url}{path}",
                data=payload,
                headers=headers,
                timeout=current_app.config.get("PEER_REQUEST_TIMEOUT", 5),
                verify=False,  # self-signed cert
            )
            resp.raise_for_status()
            logger.info("Successfully announced to peer %s", peer_base_url)
            return True
        except Exception as exc:
            logger.warning("Failed to announce to peer %s: %s", peer_base_url, exc)
            return False

    # ------------------------------------------------------------------
    # Ping / Health check
    # ------------------------------------------------------------------

    @staticmethod
    def ping_peer(peer: Peer) -> bool:
        """
        Ping a peer's /api/p2p/peers/ping endpoint.
        Updates peer status based on result.
        """
        import json
        from app.utils.hmac_auth import sign_p2p_request

        payload = json.dumps({"ping": True}).encode("utf-8")
        path    = "/api/p2p/peers/ping"
        headers = {
            "Content-Type": "application/json",
            **sign_p2p_request("POST", path, payload),
        }

        try:
            resp = http_requests.post(
                f"{peer.base_url}{path}",
                data=payload,
                headers=headers,
                timeout=current_app.config.get("PEER_REQUEST_TIMEOUT", 5),
                verify=False,
            )
            if resp.status_code == 200:
                peer.touch()
                db.session.commit()
                return True
        except Exception as exc:
            logger.warning("Ping failed for peer %s: %s", peer.base_url, exc)

        peer.status = "unreachable"
        db.session.commit()
        return False

    # ------------------------------------------------------------------
    # Broadcast a transaction to all active peers
    # ------------------------------------------------------------------

    @staticmethod
    def broadcast_transaction(payload_bytes: bytes) -> None:
        """
        Send the raw transaction payload to every active peer node
        via POST /api/p2p/transaction (HMAC-signed).
        """
        from app.utils.hmac_auth import sign_p2p_request

        peers = PeerService.get_active_peers()
        if not peers:
            return

        path    = "/api/p2p/transaction"
        headers_base = {"Content-Type": "application/json"}

        for peer in peers:
            headers = {
                **headers_base,
                **sign_p2p_request("POST", path, payload_bytes),
            }
            try:
                resp = http_requests.post(
                    f"{peer.base_url}{path}",
                    data=payload_bytes,
                    headers=headers,
                    timeout=current_app.config.get("PEER_REQUEST_TIMEOUT", 5),
                    verify=False,
                )
                if resp.status_code in (200, 201):
                    logger.debug("Transaction broadcast OK to %s", peer.base_url)
                else:
                    logger.warning(
                        "Broadcast to %s returned %d", peer.base_url, resp.status_code
                    )
            except Exception as exc:
                logger.warning("Broadcast failed to %s: %s", peer.base_url, exc)
                peer.status = "unreachable"

        db.session.commit()
