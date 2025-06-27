#!/bin/bash

PROTO_DIR="./proto"
OUT_DIR="./generated"

# Create output directory if it doesn't exist
rm -rf $OUT_DIR 2>/dev/null || true
mkdir -p $OUT_DIR
touch $OUT_DIR/__init__.py

# Generate Python gRPC code from .proto files
for file in $PROTO_DIR/*.proto; do
  python -m grpc_tools.protoc \
    --proto_path=$PROTO_DIR \
    --python_out=$OUT_DIR \
    --grpc_python_out=$OUT_DIR \
    --pyi_out=$OUT_DIR \
    $file
done

echo "✅ Protobuf files generated in '$OUT_DIR'"

sed -i -E 's/^import ([a-zA-Z0-9_]+_pb2)/from . import \1/' $OUT_DIR/*.py
echo "✅ Imports fixed in generated gRPC files"