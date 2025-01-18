const requestBody = {
    createTransactionWithWaitRequest: {
        waitForState: 'signed',
        type: 'utxo_transaction',
        signerType: 'api_signer',
        details: {
            type: 'utxo_partially_signed_bitcoin_transaction',
            inputs: [
                {
                    index: 0,
                    sighashTypes: [1],
                    signerIdentity: {
                        type: 'address',
                        address: 'bc1p0q2aalj3r6t7p86ls8f3u7pzq76qvz4zz8nquxkw0wvcdavyltuqg8hzkw'
                    },
                    disableTweakSigner: undefined
                }
            ],
            autoFinalize: false,
            psbtRawData: '0x70736274ff0100d4020000000273d92141207f821f4e797b0b6defe0b99125b33aebbade22829a95efcb2e9ea00000000000fffffffff55ff9830176ab1fd9774de3a0495a77ee206d8ef3fed736ed38a2e4074db06c0000000000ffffffff042202000000000000160014fb447b8b16c9e9942fb194335246a868129bbf2a2202000000000000160014c6b1b5e55035a6e8401f96baf772da8e4cd05d0aaf21000000000000160014c6b1b5e55035a6e8401f96baf772da8e4cd05d0a0000000000000000126a5d0f160100e6a233fc078088a5a9a30700000000000001012b10270000000000002251207815defe511e97e09f5f81d31e782207b4060aa211e60e1ace7b9986f584faf80001011f2202000000000000160014c6b1b5e55035a6e8401f96baf772da8e4cd05d0a2202023269ff874a3c4575cafe68d65ae313b999af5b4c2f937b1db46cb43bb6cf18e2483045022100fbe1059a9099cce6177dd4cc6a7acda10c865cded49f0e91f0e7a767440d28ba0220354c8a5c8466e9ef58d132d285ecbda4e29b5060a818e42125838fa3f265e016010000000000',
            sender: {
                address: 'bc1p0q2aalj3r6t7p86ls8f3u7pzq76qvz4zz8nquxkw0wvcdavyltuqg8hzkw',
                chain: {uniqueId: 'bitcoin_mainnet', chainType: 'utxo'},
                addressType: 'taproot'
            },
            pushMode: 'manual'
        },
        note: undefined,
        vaultId: '1cc91b9d-e75d-445e-9fa7-3c6d3e3dec30'
    },
    xIdempotenceId: undefined,
    xSignature: 'MEQCH3orf3lvPYA796AxXLA/TXW2X5N1mXnzxPKivEh0OBACIQDWtkTaD9SOf+qe9GeKKuIGywZijEZd2KXx39Jgp9AeGg==',
    xTimestamp: 1737031054058
}