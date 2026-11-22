// Compile together with AccountReader.swift using -D ACCOUNT_TEST. No Keychain or network access.
import Foundation

@main struct ReaderTests {
    static func main() async throws {
        let safe: [String: Any] = [
            "ipRestrict": true, "enableReading": true, "enableWithdrawals": false,
            "enableInternalTransfer": false, "enableMargin": false, "enableFutures": false,
            "permitsUniversalTransfer": false, "enableVanillaOptions": false, "enableFixApiTrade": false,
            "enableSpotAndMarginTrading": false, "enablePortfolioMarginTrading": false
        ]
        func encoded(_ flags: [String: Any]) throws -> Data {
            try JSONSerialization.data(withJSONObject: flags)
        }
        func denied(_ flags: [String: Any]) async throws {
            var path: [Endpoint] = []
            do {
                _ = try await balances(.binance) { endpoint in
                    path.append(endpoint)
                    return try encoded(flags)
                }
                fatalError("unsafe permissions accepted")
            } catch is ReaderError {
                precondition(path == [.permissions])
            }
        }
        for field in safe.keys {
            var missing = safe
            missing.removeValue(forKey: field)
            try await denied(missing)
            var opposite = safe
            opposite[field] = !(safe[field] as! Bool)
            try await denied(opposite)
        }
        try await denied(safe.merging(["newPermission": false]) { _, new in new })
        try await denied(safe.merging(["enableReading": 1]) { _, new in new })
        var endpoints: [Endpoint] = []
        let result = try await balances(.binance) { ep in
            endpoints.append(ep)
            if ep == .permissions { return try encoded(safe) }
            return Data(#"{"balances":[{"asset":"BTC","free":"2","locked":"3"}],"makerCommission":5}"#.utf8)
        }
        precondition(endpoints == [.permissions, .spot] && result.count == 1 && result[0].locked == "3")
        let upbit = try await balances(.upbit) { ep in
            precondition(ep == .upbit)
            return Data(#"[{"currency":"BTC","balance":"2","locked":"1","avg_buy_price":"123"}]"#.utf8)
        }
        precondition(upbit.count == 1 && upbit[0].symbol == "BTC" && upbit[0].free == "2")
        let keys = Keys(access: "access", secret: "test-secret")
        let b = try signedGET(.spot, keys: keys, now: 123, nonce: "ignored")
        precondition(b.httpMethod == "GET" && b.value(forHTTPHeaderField: "X-MBX-APIKEY") == "access")
        precondition(b.url!.query == "timestamp=123&signature=d18690c1929d226377d7a65514b2591c7393f2469d6abe7d398a75670e0318e3")
        let u = try signedGET(.upbit, keys: keys, now: 123, nonce: "fixed")
        precondition(u.httpMethod == "GET" && u.url!.absoluteString == Endpoint.upbit.rawValue)
        precondition(u.value(forHTTPHeaderField: "Authorization") == "Bearer eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3Nfa2V5IjoiYWNjZXNzIiwibm9uY2UiOiJmaXhlZCJ9.4tMLjwGgqa9a6VJrYDUqf9Az5z5DtwPIK7N_yOFA0eCKyPi-rPcrig5HVu5XjVtXTWymtsM33G0uWxk2a1jM9w")
        print("PASS: request signing, endpoint selection, permission failures, balance decoding")
    }
}
