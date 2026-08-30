def security_summary(tailnet_only, credentials, tailscale):
    return {
        "tailnet_only": bool(tailnet_only),
        "credentials": bool(credentials),
        "tailscale": tailscale,
        "https": bool((tailscale or {}).get("url", "").startswith("https://")),
        "exposure": "Tailnet only" if tailnet_only else "Direct LAN access permitted",
    }
