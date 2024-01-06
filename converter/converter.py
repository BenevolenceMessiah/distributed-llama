import os
import sys
import struct
import json
import torch
import numpy as np
from pathlib import Path
from torch import nn

def quantizeQ40(x, file):
    groupSize = 32
    groupSizeHalf = groupSize // 2
    assert(x.shape[0] % groupSize == 0)
    groups = x.reshape(-1, groupSize)
    gmax = np.max(groups, axis=1)
    gmin = np.min(groups, axis=1)
    absMax = np.where(-gmin > gmax, gmin, gmax)

    nBytes = 0
    for gi, group in enumerate(groups):
        groupAbsMax = absMax[gi]
        delta = groupAbsMax / -8
        id = (1.0 / delta) if delta else 0

        buffer = struct.pack('e', np.float16(delta).astype(np.float16))
        nBytes += 2

        for i in range(0, groupSizeHalf):
            x0 = group[i] * id + 8.5
            x1 = group[i + groupSizeHalf] * id + 8.5
            xi0 = min(15, int(x0))
            xi1 = min(15, int(x1))
            b = (xi0 & 0xF) | ((xi1 & 0xF) << 4)
            buffer += struct.pack('B', b)
            nBytes += 1
        file.write(buffer)
    print(f'Quantized {x.shape[0] * 4} bytes into {nBytes} bytes')
    return int(nBytes)

def exportTensor(file, tensor, floatType):
    tensor = nn.Parameter(tensor)
    d = tensor.detach().cpu().view(-1)
    if (floatType == 'float16'):
        d = d.to(torch.float16).numpy().astype(np.float16)
        b = struct.pack(f'{len(d)}e', *d)
        file.write(b)
        return len(b)
    elif (floatType == 'float32'):
        d = d.to(torch.float32).numpy().astype(np.float32)
        b = struct.pack(f'{len(d)}f', *d)
        file.write(b)
        return len(b)
    elif (floatType == 'q40'):
        d = d.to(torch.float32).numpy().astype(np.float32)
        return quantizeQ40(d, file)
    else:
        raise Exception('Unknown float type')

def toDict(models):
    stateDict = {}
    for name in list(models[0]):
        tensors = [model[name] for model in models]
        if len(tensors) == 1 or len(tensors[0].shape) == 1:
            stateDict[name] = tensors[0]
            continue
        is_axis_1 = (
            name.startswith('tok_embeddings.')
            or name.endswith('.attention.wo.weight')
            or name.endswith('.feed_forward.w2.weight')
        )
        axis = 1 if is_axis_1 else 0
        stateDict[name] = torch.cat(tensors, dim=axis)
        for model in models:
            del model[name]
    return stateDict

def writeHeader(outFile, p):
    header = struct.pack('iiiiiii',
        p['dim'],
        p['hidden_dim'],
        p['n_layers'],
        p['n_heads'],
        p['n_kv_heads'],
        p['vocab_size'],
        p['max_seq_len'])
    outFile.write(header)
    return len(header)

def getBytes(nNumbers, targetFloatType):
    if (targetFloatType == 'float32'):
        return int(nNumbers * 4)
    if (targetFloatType == 'float16'):
        return int(nNumbers * 2)
    if (targetFloatType == 'q40'):
        return int((nNumbers // 32) * 18)
    raise Exception('Unknown float type')

def getBlockOffsets(params, targetFloatType):
    kvDim = (params['dim'] * params['n_kv_heads']) / params['n_heads']
    rms = getBytes(params['dim'], 'float32')
    ffn = getBytes(params['dim'], 'float32')
    q = getBytes(params['dim'] * params['dim'], targetFloatType)
    k = getBytes(params['dim'] * kvDim, targetFloatType)
    v = getBytes(params['dim'] * kvDim, targetFloatType)
    wo = getBytes(params['dim'] * params['dim'], targetFloatType)
    w1 = getBytes(params['dim'] * params['hidden_dim'], targetFloatType)
    w2 = getBytes(params['hidden_dim'] * params['dim'], targetFloatType)
    w3 = getBytes(params['dim'] * params['hidden_dim'], targetFloatType)

    result = {
        'attention_norm.weight': rms,
        'ffn_norm.weight': ffn,
        'attention.wq.weight': q,
        'attention.wk.weight': k,
        'attention.wv.weight': v,
        'attention.wo.weight': wo,
        'feed_forward.w1.weight': w1,
        'feed_forward.w2.weight': w2,
        'feed_forward.w3.weight': w3
    }
    total = 0
    for key in list(result.keys()):
        result[key + '_offset'] = total
        total += result[key]
    result['_total'] = total
    return result

def convert(modelPath, outputPath, targetFloatType):
    paramsPath = os.path.join(modelPath, 'params.json')
    with open(paramsPath) as f:
        params = json.load(f)
        if (params['vocab_size'] < 1):
            raise Exception('Invalid vocab size')
        params['n_kv_heads'] = params.get('n_kv_heads') or params['n_heads']
        params['head_size'] = params['dim'] / params['n_heads']
        params['max_seq_len'] = 2048
        print(params)

    outFile = open(outputPath, 'wb')

    tokenEmbeddingBytes = getBytes(params['vocab_size'] * params['dim'], 'float32')
    rmsFinalBytes = getBytes(params['dim'], 'float32')
    wclsBytes = getBytes(params['vocab_size'] * params['dim'], targetFloatType)

    isHeaderWritten = False
    modelPaths = sorted(list(Path(modelPath).glob('consolidated.*.pth')))
    layerProcessedBytes = {}
    for modelPath in modelPaths:
        model = torch.load(modelPath, map_location='cpu')
        modelDict = toDict([model])
        if (not isHeaderWritten):
            params['hidden_dim'] = modelDict['layers.0.feed_forward.w1.weight'].shape[0]
            headerOffset = writeHeader(outFile, params)
            blockOffsets = getBlockOffsets(params, targetFloatType)
            afterBlocksOffset = int(headerOffset + tokenEmbeddingBytes + blockOffsets['_total'] * params['n_layers'])
            ropeBytes = int(getBytes(params['max_seq_len'] * params['head_size'] / 2, 'float32') * 2)
            isHeaderWritten = True

        for layerName in modelDict.keys():
            tensor = modelDict[layerName]
            print(f'🔶 Exporting {layerName} [{tensor.shape}]...')

            nameParts = layerName.split('.', 2)
            processedBytes = layerProcessedBytes.get(layerName) or 0
            if (processedBytes == -1):
                print('Layer is already completed')
                continue

            if (nameParts[0] == 'layers'):
                index = int(nameParts[1])
                layerSize = blockOffsets[nameParts[2]]
                layerOffset = blockOffsets[nameParts[2] + '_offset']
                tensorOffset = int(headerOffset + tokenEmbeddingBytes + blockOffsets['_total'] * index + layerOffset + processedBytes)
                tensorFloatType = 'float32' if (nameParts[2] == 'attention_norm.weight' or nameParts[2] == 'ffn_norm.weight') else targetFloatType
                outFile.seek(tensorOffset)
                processedBytes += exportTensor(outFile, tensor, tensorFloatType)
            elif (layerName == 'tok_embeddings.weight'):
                layerSize = tokenEmbeddingBytes
                outFile.seek(headerOffset + processedBytes)
                processedBytes += exportTensor(outFile, tensor, 'float32')
            elif (layerName == 'norm.weight'):
                layerSize = rmsFinalBytes
                outFile.seek(afterBlocksOffset + processedBytes)
                processedBytes += exportTensor(outFile, tensor, 'float32')
            elif (layerName == 'rope.freqs'):
                # We skip this layer
                processedBytes = -1
            elif (layerName == 'output.weight'):
                layerSize = wclsBytes
                tensorOffset = int(afterBlocksOffset + rmsFinalBytes + ropeBytes + processedBytes)
                outFile.seek(tensorOffset)
                processedBytes += exportTensor(outFile, tensor, targetFloatType)
            else:
                raise Exception(f'Unknown layer: {layerName}')

            if (processedBytes == layerSize):
                processedBytes = -1
                print('🔷 Layer is completed')
            elif(processedBytes > 0):
                print(f'Processed {processedBytes}/{layerSize} bytes')
            layerProcessedBytes[layerName] = processedBytes

    for layerName in layerProcessedBytes:
        processedBytes = layerProcessedBytes[layerName]
        if processedBytes >= 0:
            print(f'Layer {layerName} is not completed (processed {processedBytes} bytes)')

    outFile.close()

def usage():
    print('Usage: python convert.py <modelPath> <targetFloatType>')
    exit(1)

if __name__ == '__main__':
    if (len(sys.argv) < 3):
        usage()

    modelPath = sys.argv[1]
    targetFloatType = sys.argv[2]

    if (not modelPath or not targetFloatType in ['float16', 'float32', 'q40']):
        usage()

    modelName = modelPath.split('/')[-1]
    outputFileName = f'dllama_{modelName}_{targetFloatType}2.bin'

    print(f'Model name: {modelName}')
    print(f'Target float type: {targetFloatType}')
    print(f'Target file: {outputFileName}')

    convert(modelPath, outputFileName, targetFloatType)

    print('Done!')
