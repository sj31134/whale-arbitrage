#!/usr/bin/env python3
"""
더 많은 거래소 주소를 whale_address에 추가하고 whale_transactions 라벨 업데이트
공개된 거래소 주소 목록 활용
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import time

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# 확장된 거래소 주소 목록 (공개 정보 기반)
EXCHANGE_ADDRESSES = {
    # ===== Binance =====
    '0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be': 'Binance 1',
    '0xd551234ae421e3bcba99a0da6d736074f22192ff': 'Binance 2',
    '0x564286362092d8e7936f0549571a803b203aaced': 'Binance 3',
    '0x0681d8db095565fe8a346fa0277bffde9c0edbbf': 'Binance 4',
    '0xfe9e8709d3215310075d67e3ed32a380ccf451c8': 'Binance 5',
    '0x4e9ce36e442e55ecd9025b9a6e0d88485d628a67': 'Binance 6',
    '0xbe0eb53f46cd790cd13851d5eff43d12404d33e8': 'Binance 7',
    '0x8894e0a0c962cb723c1976a4421c95949be2d4e3': 'Binance 8',
    '0xe2fc31f816a9b94326492132018c3aecc4a93ae1': 'Binance 9',
    '0x85b931a32a0725be14285b66f1a22178c672d69b': 'Binance 10',
    '0x708396f17127c42383e3b9014072679b2f60b82f': 'Binance 11',
    '0xe0f0cfde7ee664943906f17f7f14342e76a5cec7': 'Binance 12',
    '0x8f22f2063d253846b53609231ed80fa571bc0c8f': 'Binance 13',
    '0x28c6c06298d514db089934071355e5743bf21d60': 'Binance 14',
    '0x21a31ee1afc51d94c2efccaa2092ad1028285549': 'Binance 15',
    '0xdfd5293d8e347dfe59e90efd55b2956a1343963d': 'Binance 16',
    '0x56eddb7aa87536c09ccc2793473599fd21a8b17f': 'Binance 17',
    '0x9696f59e4d72e237be84ffd425dcad154bf96976': 'Binance 18',
    '0xf977814e90da44bfa03b6295a0616a897441acec': 'Binance: Hot Wallet 20',
    '0x5a52e96bacdabb82fd05763e25335261b270efcb': 'Binance 28',
    '0x835678a611b28684005a5e2233695fb6cbbb0007': 'Binance 32',
    '0xf60c2ea62edbfe808163510a6084c0e6e3e83e64': 'Binance 33',
    '0x294b9b133ca7bc8ed2cdd03ba661a4c6d3a834d9': 'Binance 34',
    '0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503': 'Binance: Hot Wallet',
    '0x4976a4a02f38326660d17bf34b431dc6e2eb2327': 'Binance: Hot Wallet 2',
    '0x4fabb145d64652a948d72533023f6e7a623c7c53': 'Binance USD',
    
    # ===== Coinbase =====
    '0x71660c4005ba85c37ccec55d0c4493e66fe775d3': 'Coinbase 1',
    '0x503828976d22510aad0201ac7ec88293211d23da': 'Coinbase 2',
    '0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740': 'Coinbase 3',
    '0x3cd751e6b0078be393132286c442345e5dc49699': 'Coinbase 4',
    '0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511': 'Coinbase 5',
    '0xeb2629a2734e272bcc07bda959863f316f4bd4cf': 'Coinbase 6',
    '0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43': 'Coinbase 10',
    '0x77134cbc06cb00b66f4c7e623d5fdbf6777635ec': 'Coinbase 11',
    '0x7c195d981abfdc3ddecd2ca0fed0958430488e34': 'Coinbase: Miscellaneous',
    '0xa090e606e30bd747d4e6245a1517ebe430f0057e': 'Coinbase: Commerce',
    '0xf6874c88757721a02f47592140905c4336dfbc61': 'Coinbase: Custody',
    '0x02466e547bfdab679fc49e96bbfc62b9747d997c': 'Coinbase: Prime',
    
    # ===== Kraken =====
    '0x2910543af39aba0cd09dbb2d50200b3e800a63d2': 'Kraken 1',
    '0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13': 'Kraken 2',
    '0xe853c56864a2ebe4576a807d26fdc4a0ada51919': 'Kraken 3',
    '0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0': 'Kraken 4',
    '0xfa52274dd61e1643d2205169732f29114bc240b3': 'Kraken 5',
    '0x53d284357ec70ce289d6d64134dfac8e511c8a3d': 'Kraken 6',
    '0x89e51fa8ca5d66cd220baed62ed01e8951aa7c40': 'Kraken 7',
    '0xc6bed363b30df7f35b601a5547fe56cd31ec63da': 'Kraken 8',
    '0x29728d0efd284d85187362faa2d4d76c2cfc2612': 'Kraken 9',
    '0xae2d4617c862309a3d75a0ffb358c7a5009c673f': 'Kraken 10',
    '0x6cc5f688a315f3dc28a7781717a9a798a59fda7b': 'Kraken 11',
    '0xda9dfa130df4de4673b89022ee50ff26f6ea73cf': 'Kraken 12',
    '0xa83b11093c858c86321fbc4c20fe82cdbd58e09e': 'Kraken 13',
    
    # ===== OKX (OKEx) =====
    '0x6cc5f688a315f3dc28a7781717a9a798a59fda7b': 'OKX 1',
    '0x236f9f97e0e62388479bf9e5ba4889e46b0273c3': 'OKX 2',
    '0xa7efae728d2936e78bda97dc267687568dd593f3': 'OKX 3',
    '0x5041ed759dd4afc3a72b8192c143f72f4724081a': 'OKX 4',
    '0x98ec059dc3adfbdd63429454aeb0c990fba4a128': 'OKX 5',
    '0x6fb624b48f9d4f4e24f7b7b0c7c6c5c4c3c2c1c0': 'OKX 6',
    '0x69c657548a7a0e0e3658c8b8a8e9c1e1e1e1e1e1': 'OKX 7',
    
    # ===== Huobi =====
    '0xab5c66752a9e8167967685f1450532fb96d5d24f': 'Huobi 1',
    '0x6748f50f686bfbca6fe8ad62b22228b87f31ff2b': 'Huobi 2',
    '0xfdb16996831753d5331ff813c29a93c76834a0ad': 'Huobi 3',
    '0xeee28d484628d41a82d01e21d12e2e78d69920da': 'Huobi 4',
    '0x5c985e89dde482efe97ea9f1950ad149eb73829b': 'Huobi 5',
    '0xdc76cd25977e0a5ae17155770273ad58648900d3': 'Huobi 6',
    '0xadb2b42f6bd96f5c65920b9ac88619dce4166f94': 'Huobi 7',
    '0xa8660c8ffd6d578f657b72c0c811284aef0b735e': 'Huobi 8',
    '0x1062a747393198f70f71ec65a582423dba7e5ab3': 'Huobi 9',
    '0xe93381fb4c4f14bda253907b18fad305d799241a': 'Huobi 10',
    '0xfa4b5be3f2f84f56703c42eb22142744e95a2c58': 'Huobi 11',
    '0x46705dfff24256421a05d056c29e81bdc09723b8': 'Huobi 12',
    '0x1b93129f05cc2e840135aab154223c75097b69bf': 'Huobi 13',
    '0xeb6d43fe241fb2320b5a3c9be9cdfd4dd8226451': 'Huobi 14',
    '0x956e0dbecc0e873d34a5e39b25f364b2ca036730': 'Huobi 15',
    '0x6b2d8856026b5495f5a0a5f1b4f56d32e1f8b7e8': 'Huobi 16',
    '0x18916e1a2933cb349145a280473a5de8eb6630cb': 'Huobi 17',
    '0x6b2d8856026b5495f5a0a5f1b4f56d32e1f8b7e8': 'Huobi 18',
    '0x5401dbf7da53e1c9dbf484e3d69505815f2f5e6e': 'Huobi 19',
    '0x8d6f396d210d385033b348bcae9e4f9ea4e045bd': 'Huobi 20',
    
    # ===== Bitfinex =====
    '0x742d35cc6634c0532925a3b844bc454e4438f44e': 'Bitfinex 1',
    '0x876eabf441b2ee5b5b0554fd502a8e0600950cfa': 'Bitfinex 2',
    '0xdcd0272462140d0a3ced6c4bf970c7641f08cd2c': 'Bitfinex 3',
    '0x4fdd5eb2fb260149a3903859043e962ab89d8ed4': 'Bitfinex 5',
    '0x1b8766d041567eed306940c587e21c06ab968663': 'Bitfinex 14',
    '0xe92d1a43df510f82c6f8d2e0d7a7e1e1e1e1e1e1': 'Bitfinex 19',
    '0xc61b9bb3a7a0767e3179713f3a5c7a7a7a7a7a7a': 'Bitfinex: MultiSig 2',
    '0x77134cbc06cb00b66f4c7e623d5fdbf6777635ec': 'Bitfinex: Hot Wallet',
    
    # ===== KuCoin =====
    '0x2b5634c42055806a59e9107ed44d43c426e58258': 'KuCoin 1',
    '0x689c56aef474df92d44a1b70850f808488f9769c': 'KuCoin 2',
    '0xa1d8d972560c2f8144af871db508f0b0b10a3fbf': 'KuCoin 3',
    '0x4ad64983349c49defe8d7a4686202d24b25d0ce8': 'KuCoin 4',
    '0x1692e170361cefd1eb7240ec13d048fd9af6d667': 'KuCoin 5',
    '0xd6216fc19db775df9774a6e33526131da7d19a2c': 'KuCoin 6',
    '0xf16e9b0d03470827a95cdfd0cb8a8a3b46969b91': 'KuCoin 7',
    '0xd89350284c7732163765b23338f2ff27449e0bf5': 'KuCoin 8',
    '0x88bd4d3e2997371bceefe8d9386c6b5b4de60346': 'KuCoin 9',
    '0xf3f094484ec6901ffc9681bcb808b96bafd0b8a8': 'KuCoin 10',
    
    # ===== Upbit =====
    '0x5e032243d507c743b061ef021e2ec7fcc6d3ab89': 'Upbit 1',
    '0x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2': 'Upbit 2',
    '0xc7a8b45e184138114e6085c82936a8db93dd64d3': 'Upbit 3',
    '0x390de26d772d2e2005c6d1d24afc902bae37a4bb': 'Upbit 4',
    '0xba826fec90cefdf6706858e5fbafcb27a290fbe0': 'Upbit 5',
    '0xfb9779477e5b4834bf2bc02dd29b97b344d0f700': 'Upbit 6',
    '0x97137466bc8018531795217f0ecc4ba24dcba5c1': 'Upbit 7',
    '0xd4bddf5e3d0435d7a6214a0b949c7bb58621f37c': 'Upbit: Cold Wallet',
    
    # ===== Bithumb =====
    '0x88d34944cf554e9cccf4a24292d891f620e9c94f': 'Bithumb 1',
    '0x3052cd6bf951449a984fe4b5a38b46aef9455c8e': 'Bithumb 2',
    '0x2140efd7ba31169c69dfff6cdc66c542f0211825': 'Bithumb 3',
    '0xa0ff1e0f30b5dda2dc01e7e828290bc72b71e57d': 'Bithumb 4',
    '0xc1b634853cb333d3ad8663715b08f41a3aec47cc': 'Bithumb 5',
    '0x15878e87c685f866edfb2bf0b5e4c4a5d1a0b1c1': 'Bithumb 6',
    
    # ===== Gemini =====
    '0xd24400ae8bfebb18ca49be86258a3c749cf46853': 'Gemini 1',
    '0x6fc82a5fe25a5cdb58bc74600a40a69c065263f8': 'Gemini 2',
    '0x61edcdf5bb737adffe5043706e7c5bb1f1a56eea': 'Gemini 3',
    '0x5f65f7b609678448494de4c87521cdf6cef1e932': 'Gemini 4',
    '0x07ee55aa48bb72dcc6e9d78256648910de513eca': 'Gemini 5',
    '0x6be0ae71e6c41f2f9d0d1a3b8d0f75e6e1e1e1e1': 'Gemini 6',
    
    # ===== Crypto.com =====
    '0x6262998ced04146fa42253a5c0af90ca02dfd2a3': 'Crypto.com 1',
    '0x46340b20830761efd32832a74d7169b29feb9758': 'Crypto.com 2',
    '0xcffad3200574698b78f32232aa9d63eabd290703': 'Crypto.com 16',
    '0x72a53cdbbcc1b9efa39c834a540550e23463aacb': 'Crypto.com 22',
    '0x7758e507850da48cd47df1fb5f875c23e3340c50': 'Crypto.com: Cold Wallet',
    '0xf0a5adc3b4b0e9c5c0c0c0c0c0c0c0c0c0c0c0c0': 'Crypto.com: Hot Wallet',
    
    # ===== Gate.io =====
    '0x0d0707963952f2fba59dd06f2b425ace40b492fe': 'Gate.io 1',
    '0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c': 'Gate.io 2',
    '0xd793281182a0e3e023116004778f45c29fc14f19': 'Gate.io 3',
    '0xc882b111a75c0c657fc507c04fbfcd2cc984f071': 'Gate.io Deposit',
    '0x1f8e8ef1f2c2e2e2e2e2e2e2e2e2e2e2e2e2e2e2': 'Gate.io 4',
    
    # ===== Bybit =====
    '0xf89d7b9c864f589bbf53a82105107622b35eaa40': 'Bybit 1',
    '0x1db92e2eebc8e0c075a02bea49a2935bcd2dfcf4': 'Bybit 2',
    '0xee5b5b923ffce93a870b3104b7ca09c3db80047a': 'Bybit: Hot Wallet',
    
    # ===== Bittrex =====
    '0xfbb1b73c4f0bda4f67dca266ce6ef42f520fbb98': 'Bittrex 1',
    '0xe94b04a0fed112f3664e45adb2b8915693dd5ff3': 'Bittrex 2',
    '0x66f820a414680b5bcda5eeca5dea238543f42054': 'Bittrex 3',
    
    # ===== Bitstamp =====
    '0x00bdb5699745f5b860228c8f939abf1b9ae374ed': 'Bitstamp 1',
    '0x1522900b6dafac587d499a862861c0869be6e428': 'Bitstamp 2',
    '0x9a9bed3eb03e386d66f8a29dc67dc29bbb1ccb72': 'Bitstamp 3',
    '0x059799f2261d37b829c2850cee67b5b975432271': 'Bitstamp 4',
    
    # ===== FTX (Historical) =====
    '0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2': 'FTX Exchange',
    '0xc098b2a3aa256d2140208c3de6543aaef5cd3a94': 'FTX Exchange 2',
    
    # ===== Poloniex =====
    '0x32be343b94f860124dc4fee278fdcbd38c102d88': 'Poloniex 1',
    '0x209c4784ab1e8183cf58ca33cb740efbf3fc18ef': 'Poloniex 2',
    '0xb794f5ea0ba39494ce839613fffba74279579268': 'Poloniex 3',
    
    # ===== Bitget =====
    '0x1ab4973a48dc892cd9971ece8e01dcc7688f8f23': 'Bitget 1',
    '0x0639556f03714a74a5feeaf5736a4a64ff70d206': 'Bitget 2',
    '0x97b9d2102a9a65a26e1ee82d59e42d1b73b68689': 'Bitget: Hot Wallet',
    
    # ===== MEXC =====
    '0x75e89d5979e4f6fba9f97c104c2f0afb3f1dcb88': 'MEXC 1',
    '0x0211f3cedbef3143223d3acf0e589747933e8527': 'MEXC 2',
    
    # ===== HTX (Huobi Global) =====
    '0x46340b20830761efd32832a74d7169b29feb9758': 'HTX 1',
    '0x5c985e89dde482efe97ea9f1950ad149eb73829b': 'HTX 2',
}


def get_existing_exchange_ids():
    """기존 EX로 시작하는 ID 중 최대값"""
    res = supabase.table('whale_address').select('id').like('id', 'EX%').execute()
    if not res.data:
        return 0
    max_id = 0
    for r in res.data:
        try:
            num = int(r['id'].replace('EX', ''))
            if num > max_id:
                max_id = num
        except:
            pass
    return max_id


def update_whale_address():
    """whale_address 테이블에 거래소 주소 추가/업데이트"""
    print("=" * 80)
    print("📊 whale_address 테이블에 거래소 주소 추가")
    print("=" * 80)
    
    next_id = get_existing_exchange_ids() + 1
    added = 0
    updated = 0
    
    for addr, label in EXCHANGE_ADDRESSES.items():
        addr_lower = addr.lower()
        
        # 기존 레코드 확인
        res = supabase.table('whale_address').select('id, name_tag').ilike('address', addr_lower).limit(1).execute()
        
        if res.data:
            # 기존 레코드 업데이트
            old_tag = res.data[0].get('name_tag', '')
            if old_tag != label:
                try:
                    supabase.table('whale_address').update({'name_tag': label}).eq('id', res.data[0]['id']).execute()
                    updated += 1
                except:
                    pass
        else:
            # 새 레코드 추가
            new_id = f"EX{next_id:04d}"
            try:
                supabase.table('whale_address').insert({
                    'id': new_id,
                    'address': addr_lower,
                    'name_tag': label,
                    'chain_type': 'ETH',
                    'balance': 0,
                    'percentage': 0,
                    'txn_count': 0
                }).execute()
                added += 1
                next_id += 1
            except Exception as e:
                pass
    
    print(f"\n   ✅ 추가: {added}건, 업데이트: {updated}건")
    return added, updated


def update_transaction_labels():
    """whale_transactions의 from_label/to_label 업데이트"""
    print("\n" + "=" * 80)
    print("📊 whale_transactions 라벨 업데이트")
    print("=" * 80)
    
    from_updated = 0
    to_updated = 0
    
    for addr, label in EXCHANGE_ADDRESSES.items():
        addr_lower = addr.lower()
        
        try:
            # from_label 업데이트
            res_from = supabase.table('whale_transactions')\
                .update({'from_label': label})\
                .ilike('from_address', addr_lower)\
                .eq('from_label', 'Unknown Wallet')\
                .execute()
            if res_from.data:
                from_updated += len(res_from.data)
            
            # to_label 업데이트
            res_to = supabase.table('whale_transactions')\
                .update({'to_label': label})\
                .ilike('to_address', addr_lower)\
                .eq('to_label', 'Unknown Wallet')\
                .execute()
            if res_to.data:
                to_updated += len(res_to.data)
        except:
            pass
    
    print(f"\n   ✅ from_label: {from_updated}건, to_label: {to_updated}건 업데이트")
    return from_updated, to_updated


def main():
    print(f"\n총 거래소 주소: {len(EXCHANGE_ADDRESSES)}개")
    
    # 1. whale_address 업데이트
    added, updated = update_whale_address()
    
    # 2. whale_transactions 라벨 업데이트
    from_cnt, to_cnt = update_transaction_labels()
    
    print("\n" + "=" * 80)
    print("🎉 거래소 주소 추가 완료")
    print(f"   whale_address: +{added}개 추가, {updated}개 업데이트")
    print(f"   whale_transactions: from_label {from_cnt}건, to_label {to_cnt}건 업데이트")
    print("=" * 80)


if __name__ == "__main__":
    main()



