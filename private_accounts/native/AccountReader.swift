// macOS-only keychain and request signing. Secrets are never returned to the caller.
import Foundation
import CryptoKit
import Security
import Darwin
import CoreFoundation

struct ReaderError: Error {
    let message: String
    init(_ message: String) { self.message = message }
}

enum Exchange: String { case upbit, binance }
struct Keys: Codable { let access: String; let secret: String }
struct Balance: Codable { let symbol: String; let free: String; let locked: String }

func prompt(_ label: String, hidden: Bool = true) throws -> String {
    var buffer = [CChar](repeating: 0, count: 1024)
    defer { buffer.withUnsafeMutableBytes { _ = memset_s($0.baseAddress!, $0.count, 0, $0.count) } }
    guard readpassphrase(label, &buffer, buffer.count, RPP_REQUIRE_TTY | (hidden ? 0 : RPP_ECHO_ON)) != nil else {
        throw ReaderError("개인 Mac의 대화형 터미널에서 입력하세요.")
    }
    let value = String(cString: buffer)
    guard !value.isEmpty, value.utf8.count < buffer.count - 1,
          value.utf8.allSatisfy({ $0 >= 33 && $0 <= 126 }) else {
        throw ReaderError("입력 형식이 올바르지 않습니다.")
    }
    return value
}

struct Vault {
    let exchange: Exchange
    let alias: String
    var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: "whale-tracking.readonly." + exchange.rawValue,
         kSecAttrAccount as String: alias,
         kSecAttrSynchronizable as String: false]
    }
    func load() throws -> Keys {
        var q = query
        q[kSecReturnData as String] = true
        var result: CFTypeRef?
        let status = SecItemCopyMatching(q as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data,
              let keys = try? JSONDecoder().decode(Keys.self, from: data) else {
            throw ReaderError("키체인에서 키를 읽지 못했습니다. 연결 등록 또는 키체인 잠금을 확인하세요.")
        }
        return keys
    }
    func save(_ keys: Keys) throws {
        let fields = [kSecValueData as String: try JSONEncoder().encode(keys)]
        var attributes = query.merging(fields) { _, new in new }
        // A nil trusted list gives the creating executable access under the login keychain ACL.
        var access: SecAccess?
        guard SecAccessCreate("Whale Tracking read-only collector" as CFString, nil, &access) == errSecSuccess,
              let acl = access else { throw ReaderError("키체인 접근 제어 설정 실패") }
        attributes[kSecAttrAccess as String] = acl
        var status = SecItemAdd(attributes as CFDictionary, nil)
        if status == errSecDuplicateItem {
            status = SecItemUpdate(query as CFDictionary, fields as CFDictionary)
        }
        guard status == errSecSuccess else { throw ReaderError("키체인 저장 실패 (\(status))") }
    }
    func forget() throws {
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw ReaderError("키체인 항목 삭제 실패 (\(status))")
        }
    }
}

// A fixed GET allowlist and disabled redirects keep authenticated requests on their original host.
enum Endpoint: String {
    case upbit = "https://api.upbit.com/v1/accounts"
    case permissions = "https://api.binance.com/sapi/v1/account/apiRestrictions"
    case spot = "https://api.binance.com/api/v3/account"
}
final class NoRedirect: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest,
        completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
}

func signedGET(_ endpoint: Endpoint, keys: Keys, now: Int64, nonce: String) throws -> URLRequest {
    let secret = SymmetricKey(data: Data(keys.secret.utf8))
    var url = URLComponents(string: endpoint.rawValue)!
    var headers: [String: String] = [:]
    if endpoint == .upbit {
        func encode(_ data: Data) -> String {
            data.base64EncodedString().replacingOccurrences(of: "+", with: "-")
                .replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
        }
        let header = Data(#"{"alg":"HS512","typ":"JWT"}"#.utf8)
        let payload = try JSONSerialization.data(withJSONObject: ["access_key": keys.access, "nonce": nonce],
                                                  options: [.sortedKeys])
        let token = encode(header) + "." + encode(payload)
        let signature = HMAC<SHA512>.authenticationCode(for: Data(token.utf8), using: secret)
        headers["Authorization"] = "Bearer " + token + "." + encode(Data(signature))
    } else {
        let query = "timestamp=\(now)"
        let mac = HMAC<SHA256>.authenticationCode(for: Data(query.utf8), using: secret)
        url.percentEncodedQuery = query + "&signature=" + mac.map { String(format: "%02x", $0) }.joined()
        headers["X-MBX-APIKEY"] = keys.access
    }
    var request = URLRequest(url: url.url!)
    request.httpMethod = "GET"
    request.allHTTPHeaderFields = headers
    return request
}

func verifyBinance(_ data: Data) throws {
    let restricted = ["enableWithdrawals", "enableInternalTransfer", "enableMargin", "enableFutures",
                      "permitsUniversalTransfer", "enableVanillaOptions", "enableFixApiTrade",
                      "enableSpotAndMarginTrading", "enablePortfolioMarginTrading"]
    let error = ReaderError("바이낸스 키 권한을 확인하세요. 읽기 및 IP 제한을 켜고 거래·이체 권한을 모두 꺼야 합니다.")
    guard let fields = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw error }
    func flag(_ name: String) -> Bool? {
        guard let n = fields[name] as? NSNumber, CFGetTypeID(n) == CFBooleanGetTypeID() else { return nil }
        return n.boolValue
    }
    guard flag("enableReading") == true, flag("ipRestrict") == true,
          restricted.allSatisfy({ flag($0) == false }) else { throw error }
    let known = Set(restricted + ["enableReading", "ipRestrict", "createTime", "tradingAuthorityExpirationTime", "enableFixReadOnly"])
    guard Set(fields.keys).isSubset(of: known) else { throw ReaderError("미확인 바이낸스 권한 필드가 있어 동기화를 중단했습니다.") }
}

struct UpbitRow: Decodable { let currency, balance, locked: String }
struct SpotRow: Decodable { let asset, free, locked: String }
struct SpotAccount: Decodable { let balances: [SpotRow] }

func balances(_ exchange: Exchange, fetch: (Endpoint) async throws -> Data) async throws -> [Balance] {
    let decoder = JSONDecoder()
    if exchange == .upbit {
        let rows = try decoder.decode([UpbitRow].self, from: try await fetch(.upbit))
        return rows.map { Balance(symbol: $0.currency, free: $0.balance, locked: $0.locked) }
    }
    try verifyBinance(try await fetch(.permissions))
    let account = try decoder.decode(SpotAccount.self, from: try await fetch(.spot))
    return account.balances.map { Balance(symbol: $0.asset, free: $0.free, locked: $0.locked) }
}

func fetchBalances(_ exchange: Exchange, _ keys: Keys) async throws -> [Balance] {
    let config = URLSessionConfiguration.ephemeral
    config.httpCookieStorage = nil
    config.urlCredentialStorage = nil
    config.urlCache = nil
    config.timeoutIntervalForRequest = 15
    config.timeoutIntervalForResource = 30
    let session = URLSession(configuration: config, delegate: NoRedirect(), delegateQueue: nil)
    defer { session.invalidateAndCancel() }
    return try await balances(exchange) { endpoint in
        let request = try signedGET(endpoint, keys: keys, now: Int64(Date().timeIntervalSince1970 * 1000),
                                    nonce: UUID().uuidString)
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw ReaderError("거래소 조회 실패 (HTTP \((response as? HTTPURLResponse)?.statusCode ?? 0)). 권한·IP·시계를 확인하세요.")
        }
        return data
    }
}

#if !ACCOUNT_TEST
@main struct AccountReader {
    static func main() async {
        do {
            let args = Array(CommandLine.arguments.dropFirst())
            if args == ["--supports-env"] { print("1"); return }
            guard args.count == 3, let exchange = Exchange(rawValue: args[1]),
                  args[2].range(of: #"\A[a-zA-Z0-9_-]{1,32}\z"#, options: .regularExpression) != nil
            else { throw ReaderError("개인 계좌 CLI를 통해 실행하세요.") }
            let vault = Vault(exchange: exchange, alias: args[2])
            switch args[0] {
            case "connect", "connect-env":
                if exchange == .upbit {
                    let answer = try prompt("업비트 발급 화면에서 자산조회만 선택하고 허용 IP를 등록했으면 READONLY 입력: ", hidden: false)
                    guard answer == "READONLY" else { throw ReaderError("업비트 권한 확인을 취소했습니다.") }
                }
                let keys: Keys
                if args[0] == "connect-env" {
                    let data = FileHandle.standardInput.readData(ofLength: 8193)
                    guard data.count <= 8192, let parsed = try? JSONDecoder().decode(Keys.self, from: data),
                          [parsed.access, parsed.secret].allSatisfy({ !$0.isEmpty && $0.utf8.count <= 1022 &&
                              $0.utf8.allSatisfy({ $0 >= 33 && $0 <= 126 }) }) else {
                        throw ReaderError("로컬 키 입력을 확인하세요.")
                    }
                    keys = parsed
                } else {
                    keys = Keys(access: try prompt("Access/API key: "), secret: try prompt("Secret key: "))
                }
                _ = try await fetchBalances(exchange, keys)
                try vault.save(keys)
            case "sync":
                let rows = try await fetchBalances(exchange, vault.load())
                FileHandle.standardOutput.write(try JSONEncoder().encode(rows))
            case "disconnect": try vault.forget()
            default: throw ReaderError("지원하지 않는 작업입니다.")
            }
        } catch {
            // Foundation errors may contain a signed URL; never echo their description.
            fputs((error as? ReaderError)?.message ?? "조회 응답 또는 네트워크 오류", stderr)
            fputs("\n", stderr)
            exit(1)
        }
    }
}
#endif
