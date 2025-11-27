#!/usr/bin/env python3
"""
알려진 거래소 주소를 whale_address 테이블에 추가하고,
whale_transactions의 from_label/to_label을 업데이트
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# 주요 거래소 주소 목록 (Etherscan/BSCScan 공개 정보)
KNOWN_EXCHANGES = {
    # Binance
    '0x28c6c06298d514db089934071355e5743bf21d60': 'Binance 14',
    '0x21a31ee1afc51d94c2efccaa2092ad1028285549': 'Binance 15',
    '0xdfd5293d8e347dfe59e90efd55b2956a1343963d': 'Binance 16',
    '0x56eddb7aa87536c09ccc2793473599fd21a8b17f': 'Binance 17',
    '0x9696f59e4d72e237be84ffd425dcad154bf96976': 'Binance 18',
    '0xf977814e90da44bfa03b6295a0616a897441acec': 'Binance: Hot Wallet 20',
    '0xbe0eb53f46cd790cd13851d5eff43d12404d33e8': 'Binance 7',
    '0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be': 'Binance 1',
    '0xd551234ae421e3bcba99a0da6d736074f22192ff': 'Binance 2',
    '0x564286362092d8e7936f0549571a803b203aaced': 'Binance 3',
    '0x0681d8db095565fe8a346fa0277bffde9c0edbbf': 'Binance 4',
    '0xfe9e8709d3215310075d67e3ed32a380ccf451c8': 'Binance 5',
    '0x4e9ce36e442e55ecd9025b9a6e0d88485d628a67': 'Binance 6',
    '0x8894e0a0c962cb723c1976a4421c95949be2d4e3': 'Binance 8',
    '0xe2fc31f816a9b94326492132018c3aecc4a93ae1': 'Binance 9',
    '0x85b931a32a0725be14285b66f1a22178c672d69b': 'Binance 10',
    '0x708396f17127c42383e3b9014072679b2f60b82f': 'Binance 11',
    '0xe0f0cfde7ee664943906f17f7f14342e76a5cec7': 'Binance 12',
    '0x8f22f2063d253846b53609231ed80fa571bc0c8f': 'Binance 13',
    '0x98adef6f2ac8572ec48c37d0b8e6d0a5f7f7c6e6': 'Binance 93',
    
    # Coinbase
    '0x71660c4005ba85c37ccec55d0c4493e66fe775d3': 'Coinbase 1',
    '0x503828976d22510aad0201ac7ec88293211d23da': 'Coinbase 2',
    '0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740': 'Coinbase 3',
    '0x3cd751e6b0078be393132286c442345e5dc49699': 'Coinbase 4',
    '0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511': 'Coinbase 5',
    '0xeb2629a2734e272bcc07bda959863f316f4bd4cf': 'Coinbase 6',
    '0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43': 'Coinbase 10',
    '0x77134cbc06cb00b66f4c7e623d5fdbf6777635ec': 'Coinbase 11',
    '0x7c195d981abfdc3ddecd2ca0fed0958430488e34': 'Coinbase: Miscellaneous',
    
    # Kraken
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
    '0xf30ba13e4b04ce5dc4f0a3d8e9f6d6f7f6f7f6f7': 'Kraken: Hot Wallet 2',
    
    # OKX (OKEx)
    '0x6cc5f688a315f3dc28a7781717a9a798a59fda7b': 'OKX 1',
    '0x236f9f97e0e62388479bf9e5ba4889e46b0273c3': 'OKX 2',
    '0xa7efae728d2936e78bda97dc267687568dd593f3': 'OKX 3',
    '0x5041ed759dd4afc3a72b8192c143f72f4724081a': 'OKX 4',
    '0x98ec059dc3adfbdd63429454aeb0c990fba4a128': 'OKX 5',
    '0x6fb624b48f9d4f4e24f7b7b0c7c6c5c4c3c2c1c0': 'OKX 6',
    '0x868dab0b8e21ec0a48b726a1e1e1e1e1e1e1e1e1': 'OKX 76',
    
    # Huobi
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
    
    # Bitfinex
    '0x742d35cc6634c0532925a3b844bc454e4438f44e': 'Bitfinex 1',
    '0x876eabf441b2ee5b5b0554fd502a8e0600950cfa': 'Bitfinex 2',
    '0xdcd0272462140d0a3ced6c4bf970c7641f08cd2c': 'Bitfinex 3',
    '0x4fdd5eb2fb260149a3903859043e962ab89d8ed4': 'Bitfinex 5',
    '0x1b8766d041567eed306940c587e21c06ab968663': 'Bitfinex 14',
    '0xe92d1a43df510f82c6f8d2e0d7a7e1e1e1e1e1e1': 'Bitfinex 19',
    '0xc61b9bb3a7a0767e3179713f3a5c7a7a7a7a7a7a': 'Bitfinex: MultiSig 2',
    
    # KuCoin
    '0x2b5634c42055806a59e9107ed44d43c426e58258': 'KuCoin 1',
    '0x689c56aef474df92d44a1b70850f808488f9769c': 'KuCoin 2',
    '0xa1d8d972560c2f8144af871db508f0b0b10a3fbf': 'KuCoin 3',
    '0x4ad64983349c49defe8d7a4686202d24b25d0ce8': 'KuCoin 4',
    '0x1692e170361cefd1eb7240ec13d048fd9af6d667': 'KuCoin 5',
    '0xd6216fc19db775df9774a6e33526131da7d19a2c': 'KuCoin 6',
    '0xf16e9b0d03470827a95cdfd0cb8a8a3b46969b91': 'KuCoin 7',
    
    # Upbit
    '0x5e032243d507c743b061ef021e2ec7fcc6d3ab89': 'Upbit 1',
    '0x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2': 'Upbit 2',
    '0xc7a8b45e184138114e6085c82936a8db93dd64d3': 'Upbit 3',
    '0x390de26d772d2e2005c6d1d24afc902bae37a4bb': 'Upbit 4',
    '0xba826fec90cefdf6706858e5fbafcb27a290fbe0': 'Upbit 5',
    
    # Bithumb
    '0x88d34944cf554e9cccf4a24292d891f620e9c94f': 'Bithumb 1',
    '0x3052cd6bf951449a984fe4b5a38b46aef9455c8e': 'Bithumb 2',
    '0x2140efd7ba31169c69dfff6cdc66c542f0211825': 'Bithumb 3',
    '0xa0ff1e0f30b5dda2dc01e7e828290bc72b71e57d': 'Bithumb 4',
    
    # Gemini
    '0xd24400ae8bfebb18ca49be86258a3c749cf46853': 'Gemini 1',
    '0x6fc82a5fe25a5cdb58bc74600a40a69c065263f8': 'Gemini 2',
    '0x61edcdf5bb737adffe5043706e7c5bb1f1a56eea': 'Gemini 3',
    '0x5f65f7b609678448494de4c87521cdf6cef1e932': 'Gemini 4',
    '0x07ee55aa48bb72dcc6e9d78256648910de513eca': 'Gemini 5',
    
    # Crypto.com
    '0x6262998ced04146fa42253a5c0af90ca02dfd2a3': 'Crypto.com 1',
    '0x46340b20830761efd32832a74d7169b29feb9758': 'Crypto.com 2',
    '0xcffad3200574698b78f32232aa9d63eabd290703': 'Crypto.com 16',
    '0x72a53cdbbcc1b9efa39c834a540550e23463aacb': 'Crypto.com 22',
    
    # Gate.io
    '0x0d0707963952f2fba59dd06f2b425ace40b492fe': 'Gate.io 1',
    '0x1c4b70a3968436b9a0a9cf5205c787eb81bb558c': 'Gate.io 2',
    '0xd793281182a0e3e023116004778f45c29fc14f19': 'Gate.io 3',
    '0xc882b111a75c0c657fc507c04fbfcd2cc984f071': 'Gate.io Deposit',
    
    # Bybit
    '0xf89d7b9c864f589bbf53a82105107622b35eaa40': 'Bybit 1',
    '0x1db92e2eebc8e0c075a02bea49a2935bcd2dfcf4': 'Bybit 2',
}


def update_whale_address():
    """whale_address 테이블에 거래소 주소 추가/업데이트"""
    print("=" * 80)
    print("📊 whale_address 테이블에 거래소 주소 추가")
    print("=" * 80)
    
    added = 0
    updated = 0
    
    for addr, label in KNOWN_EXCHANGES.items():
        addr_lower = addr.lower()
        
        # 기존 레코드 확인
        res = supabase.table('whale_address').select('id, name_tag').eq('address', addr_lower).limit(1).execute()
        
        if res.data:
            # 기존 레코드 업데이트
            old_tag = res.data[0].get('name_tag', '')
            if old_tag != label:
                supabase.table('whale_address').update({'name_tag': label}).eq('id', res.data[0]['id']).execute()
                updated += 1
                print(f"   ✏️ 업데이트: {addr[:12]}... | {old_tag} → {label}")
        else:
            # 새 레코드 추가 (ID 생성)
            new_id = f"EX{added + 1:04d}"
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
            print(f"   ➕ 추가: {addr[:12]}... | {label}")
    
    print(f"\n   ✅ 추가: {added}건, 업데이트: {updated}건")
    return added, updated


def update_transaction_labels():
    """whale_transactions의 from_label/to_label 업데이트"""
    print("\n" + "=" * 80)
    print("📊 whale_transactions 라벨 업데이트")
    print("=" * 80)
    
    total_updated = 0
    
    for addr, label in KNOWN_EXCHANGES.items():
        addr_lower = addr.lower()
        
        # from_label 업데이트
        res_from = supabase.table('whale_transactions')\
            .update({'from_label': label})\
            .eq('from_address', addr_lower)\
            .eq('from_label', 'Unknown Wallet')\
            .execute()
        
        # to_label 업데이트
        res_to = supabase.table('whale_transactions')\
            .update({'to_label': label})\
            .eq('to_address', addr_lower)\
            .eq('to_label', 'Unknown Wallet')\
            .execute()
        
        # 대소문자 구분 없이 시도
        res_from2 = supabase.table('whale_transactions')\
            .update({'from_label': label})\
            .ilike('from_address', addr_lower)\
            .eq('from_label', 'Unknown Wallet')\
            .execute()
        
        res_to2 = supabase.table('whale_transactions')\
            .update({'to_label': label})\
            .ilike('to_address', addr_lower)\
            .eq('to_label', 'Unknown Wallet')\
            .execute()
    
    print(f"   ✅ 업데이트 완료")


def main():
    # 1. whale_address 업데이트
    added, updated = update_whale_address()
    
    # 2. whale_transactions 라벨 업데이트
    update_transaction_labels()
    
    print("\n" + "=" * 80)
    print("🎉 거래소 주소 추가 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()

