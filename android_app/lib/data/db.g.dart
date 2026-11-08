// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'db.dart';

// ignore_for_file: type=lint
class $TopicsTable extends Topics with TableInfo<$TopicsTable, Topic> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $TopicsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _orderIndexMeta = const VerificationMeta(
    'orderIndex',
  );
  @override
  late final GeneratedColumn<int> orderIndex = GeneratedColumn<int>(
    'order_index',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [id, name, orderIndex, createdAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'topics';
  @override
  VerificationContext validateIntegrity(
    Insertable<Topic> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('name')) {
      context.handle(
        _nameMeta,
        name.isAcceptableOrUnknown(data['name']!, _nameMeta),
      );
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('order_index')) {
      context.handle(
        _orderIndexMeta,
        orderIndex.isAcceptableOrUnknown(data['order_index']!, _orderIndexMeta),
      );
    } else if (isInserting) {
      context.missing(_orderIndexMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  Topic map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Topic(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      name: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}name'],
      )!,
      orderIndex: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}order_index'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $TopicsTable createAlias(String alias) {
    return $TopicsTable(attachedDatabase, alias);
  }
}

class Topic extends DataClass implements Insertable<Topic> {
  final int id;
  final String name;
  final int orderIndex;
  final String createdAt;
  const Topic({
    required this.id,
    required this.name,
    required this.orderIndex,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['name'] = Variable<String>(name);
    map['order_index'] = Variable<int>(orderIndex);
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  TopicsCompanion toCompanion(bool nullToAbsent) {
    return TopicsCompanion(
      id: Value(id),
      name: Value(name),
      orderIndex: Value(orderIndex),
      createdAt: Value(createdAt),
    );
  }

  factory Topic.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Topic(
      id: serializer.fromJson<int>(json['id']),
      name: serializer.fromJson<String>(json['name']),
      orderIndex: serializer.fromJson<int>(json['orderIndex']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'name': serializer.toJson<String>(name),
      'orderIndex': serializer.toJson<int>(orderIndex),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  Topic copyWith({int? id, String? name, int? orderIndex, String? createdAt}) =>
      Topic(
        id: id ?? this.id,
        name: name ?? this.name,
        orderIndex: orderIndex ?? this.orderIndex,
        createdAt: createdAt ?? this.createdAt,
      );
  Topic copyWithCompanion(TopicsCompanion data) {
    return Topic(
      id: data.id.present ? data.id.value : this.id,
      name: data.name.present ? data.name.value : this.name,
      orderIndex: data.orderIndex.present
          ? data.orderIndex.value
          : this.orderIndex,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Topic(')
          ..write('id: $id, ')
          ..write('name: $name, ')
          ..write('orderIndex: $orderIndex, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, name, orderIndex, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Topic &&
          other.id == this.id &&
          other.name == this.name &&
          other.orderIndex == this.orderIndex &&
          other.createdAt == this.createdAt);
}

class TopicsCompanion extends UpdateCompanion<Topic> {
  final Value<int> id;
  final Value<String> name;
  final Value<int> orderIndex;
  final Value<String> createdAt;
  const TopicsCompanion({
    this.id = const Value.absent(),
    this.name = const Value.absent(),
    this.orderIndex = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  TopicsCompanion.insert({
    this.id = const Value.absent(),
    required String name,
    required int orderIndex,
    required String createdAt,
  }) : name = Value(name),
       orderIndex = Value(orderIndex),
       createdAt = Value(createdAt);
  static Insertable<Topic> custom({
    Expression<int>? id,
    Expression<String>? name,
    Expression<int>? orderIndex,
    Expression<String>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (name != null) 'name': name,
      if (orderIndex != null) 'order_index': orderIndex,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  TopicsCompanion copyWith({
    Value<int>? id,
    Value<String>? name,
    Value<int>? orderIndex,
    Value<String>? createdAt,
  }) {
    return TopicsCompanion(
      id: id ?? this.id,
      name: name ?? this.name,
      orderIndex: orderIndex ?? this.orderIndex,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (orderIndex.present) {
      map['order_index'] = Variable<int>(orderIndex.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('TopicsCompanion(')
          ..write('id: $id, ')
          ..write('name: $name, ')
          ..write('orderIndex: $orderIndex, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

class $LessonsTable extends Lessons with TableInfo<$LessonsTable, Lesson> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LessonsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _topicIdMeta = const VerificationMeta(
    'topicId',
  );
  @override
  late final GeneratedColumn<int> topicId = GeneratedColumn<int>(
    'topic_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _orderIndexMeta = const VerificationMeta(
    'orderIndex',
  );
  @override
  late final GeneratedColumn<int> orderIndex = GeneratedColumn<int>(
    'order_index',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _titleMeta = const VerificationMeta('title');
  @override
  late final GeneratedColumn<String> title = GeneratedColumn<String>(
    'title',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
    'status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _audioPathMeta = const VerificationMeta(
    'audioPath',
  );
  @override
  late final GeneratedColumn<String> audioPath = GeneratedColumn<String>(
    'audio_path',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _lastReviewedAtMeta = const VerificationMeta(
    'lastReviewedAt',
  );
  @override
  late final GeneratedColumn<String> lastReviewedAt = GeneratedColumn<String>(
    'last_reviewed_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    topicId,
    orderIndex,
    title,
    status,
    audioPath,
    createdAt,
    lastReviewedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'lessons';
  @override
  VerificationContext validateIntegrity(
    Insertable<Lesson> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('topic_id')) {
      context.handle(
        _topicIdMeta,
        topicId.isAcceptableOrUnknown(data['topic_id']!, _topicIdMeta),
      );
    } else if (isInserting) {
      context.missing(_topicIdMeta);
    }
    if (data.containsKey('order_index')) {
      context.handle(
        _orderIndexMeta,
        orderIndex.isAcceptableOrUnknown(data['order_index']!, _orderIndexMeta),
      );
    } else if (isInserting) {
      context.missing(_orderIndexMeta);
    }
    if (data.containsKey('title')) {
      context.handle(
        _titleMeta,
        title.isAcceptableOrUnknown(data['title']!, _titleMeta),
      );
    }
    if (data.containsKey('status')) {
      context.handle(
        _statusMeta,
        status.isAcceptableOrUnknown(data['status']!, _statusMeta),
      );
    } else if (isInserting) {
      context.missing(_statusMeta);
    }
    if (data.containsKey('audio_path')) {
      context.handle(
        _audioPathMeta,
        audioPath.isAcceptableOrUnknown(data['audio_path']!, _audioPathMeta),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('last_reviewed_at')) {
      context.handle(
        _lastReviewedAtMeta,
        lastReviewedAt.isAcceptableOrUnknown(
          data['last_reviewed_at']!,
          _lastReviewedAtMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  Lesson map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Lesson(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      topicId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}topic_id'],
      )!,
      orderIndex: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}order_index'],
      )!,
      title: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}title'],
      ),
      status: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}status'],
      )!,
      audioPath: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}audio_path'],
      ),
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
      lastReviewedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}last_reviewed_at'],
      ),
    );
  }

  @override
  $LessonsTable createAlias(String alias) {
    return $LessonsTable(attachedDatabase, alias);
  }
}

class Lesson extends DataClass implements Insertable<Lesson> {
  final int id;
  final int topicId;
  final int orderIndex;
  final String? title;
  final String status;

  /// File name only, e.g. `lesson_3.mp3` (same convention as the desktop).
  final String? audioPath;
  final String createdAt;
  final String? lastReviewedAt;
  const Lesson({
    required this.id,
    required this.topicId,
    required this.orderIndex,
    this.title,
    required this.status,
    this.audioPath,
    required this.createdAt,
    this.lastReviewedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['topic_id'] = Variable<int>(topicId);
    map['order_index'] = Variable<int>(orderIndex);
    if (!nullToAbsent || title != null) {
      map['title'] = Variable<String>(title);
    }
    map['status'] = Variable<String>(status);
    if (!nullToAbsent || audioPath != null) {
      map['audio_path'] = Variable<String>(audioPath);
    }
    map['created_at'] = Variable<String>(createdAt);
    if (!nullToAbsent || lastReviewedAt != null) {
      map['last_reviewed_at'] = Variable<String>(lastReviewedAt);
    }
    return map;
  }

  LessonsCompanion toCompanion(bool nullToAbsent) {
    return LessonsCompanion(
      id: Value(id),
      topicId: Value(topicId),
      orderIndex: Value(orderIndex),
      title: title == null && nullToAbsent
          ? const Value.absent()
          : Value(title),
      status: Value(status),
      audioPath: audioPath == null && nullToAbsent
          ? const Value.absent()
          : Value(audioPath),
      createdAt: Value(createdAt),
      lastReviewedAt: lastReviewedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(lastReviewedAt),
    );
  }

  factory Lesson.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Lesson(
      id: serializer.fromJson<int>(json['id']),
      topicId: serializer.fromJson<int>(json['topicId']),
      orderIndex: serializer.fromJson<int>(json['orderIndex']),
      title: serializer.fromJson<String?>(json['title']),
      status: serializer.fromJson<String>(json['status']),
      audioPath: serializer.fromJson<String?>(json['audioPath']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
      lastReviewedAt: serializer.fromJson<String?>(json['lastReviewedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'topicId': serializer.toJson<int>(topicId),
      'orderIndex': serializer.toJson<int>(orderIndex),
      'title': serializer.toJson<String?>(title),
      'status': serializer.toJson<String>(status),
      'audioPath': serializer.toJson<String?>(audioPath),
      'createdAt': serializer.toJson<String>(createdAt),
      'lastReviewedAt': serializer.toJson<String?>(lastReviewedAt),
    };
  }

  Lesson copyWith({
    int? id,
    int? topicId,
    int? orderIndex,
    Value<String?> title = const Value.absent(),
    String? status,
    Value<String?> audioPath = const Value.absent(),
    String? createdAt,
    Value<String?> lastReviewedAt = const Value.absent(),
  }) => Lesson(
    id: id ?? this.id,
    topicId: topicId ?? this.topicId,
    orderIndex: orderIndex ?? this.orderIndex,
    title: title.present ? title.value : this.title,
    status: status ?? this.status,
    audioPath: audioPath.present ? audioPath.value : this.audioPath,
    createdAt: createdAt ?? this.createdAt,
    lastReviewedAt: lastReviewedAt.present
        ? lastReviewedAt.value
        : this.lastReviewedAt,
  );
  Lesson copyWithCompanion(LessonsCompanion data) {
    return Lesson(
      id: data.id.present ? data.id.value : this.id,
      topicId: data.topicId.present ? data.topicId.value : this.topicId,
      orderIndex: data.orderIndex.present
          ? data.orderIndex.value
          : this.orderIndex,
      title: data.title.present ? data.title.value : this.title,
      status: data.status.present ? data.status.value : this.status,
      audioPath: data.audioPath.present ? data.audioPath.value : this.audioPath,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      lastReviewedAt: data.lastReviewedAt.present
          ? data.lastReviewedAt.value
          : this.lastReviewedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Lesson(')
          ..write('id: $id, ')
          ..write('topicId: $topicId, ')
          ..write('orderIndex: $orderIndex, ')
          ..write('title: $title, ')
          ..write('status: $status, ')
          ..write('audioPath: $audioPath, ')
          ..write('createdAt: $createdAt, ')
          ..write('lastReviewedAt: $lastReviewedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    topicId,
    orderIndex,
    title,
    status,
    audioPath,
    createdAt,
    lastReviewedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Lesson &&
          other.id == this.id &&
          other.topicId == this.topicId &&
          other.orderIndex == this.orderIndex &&
          other.title == this.title &&
          other.status == this.status &&
          other.audioPath == this.audioPath &&
          other.createdAt == this.createdAt &&
          other.lastReviewedAt == this.lastReviewedAt);
}

class LessonsCompanion extends UpdateCompanion<Lesson> {
  final Value<int> id;
  final Value<int> topicId;
  final Value<int> orderIndex;
  final Value<String?> title;
  final Value<String> status;
  final Value<String?> audioPath;
  final Value<String> createdAt;
  final Value<String?> lastReviewedAt;
  const LessonsCompanion({
    this.id = const Value.absent(),
    this.topicId = const Value.absent(),
    this.orderIndex = const Value.absent(),
    this.title = const Value.absent(),
    this.status = const Value.absent(),
    this.audioPath = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.lastReviewedAt = const Value.absent(),
  });
  LessonsCompanion.insert({
    this.id = const Value.absent(),
    required int topicId,
    required int orderIndex,
    this.title = const Value.absent(),
    required String status,
    this.audioPath = const Value.absent(),
    required String createdAt,
    this.lastReviewedAt = const Value.absent(),
  }) : topicId = Value(topicId),
       orderIndex = Value(orderIndex),
       status = Value(status),
       createdAt = Value(createdAt);
  static Insertable<Lesson> custom({
    Expression<int>? id,
    Expression<int>? topicId,
    Expression<int>? orderIndex,
    Expression<String>? title,
    Expression<String>? status,
    Expression<String>? audioPath,
    Expression<String>? createdAt,
    Expression<String>? lastReviewedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (topicId != null) 'topic_id': topicId,
      if (orderIndex != null) 'order_index': orderIndex,
      if (title != null) 'title': title,
      if (status != null) 'status': status,
      if (audioPath != null) 'audio_path': audioPath,
      if (createdAt != null) 'created_at': createdAt,
      if (lastReviewedAt != null) 'last_reviewed_at': lastReviewedAt,
    });
  }

  LessonsCompanion copyWith({
    Value<int>? id,
    Value<int>? topicId,
    Value<int>? orderIndex,
    Value<String?>? title,
    Value<String>? status,
    Value<String?>? audioPath,
    Value<String>? createdAt,
    Value<String?>? lastReviewedAt,
  }) {
    return LessonsCompanion(
      id: id ?? this.id,
      topicId: topicId ?? this.topicId,
      orderIndex: orderIndex ?? this.orderIndex,
      title: title ?? this.title,
      status: status ?? this.status,
      audioPath: audioPath ?? this.audioPath,
      createdAt: createdAt ?? this.createdAt,
      lastReviewedAt: lastReviewedAt ?? this.lastReviewedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (topicId.present) {
      map['topic_id'] = Variable<int>(topicId.value);
    }
    if (orderIndex.present) {
      map['order_index'] = Variable<int>(orderIndex.value);
    }
    if (title.present) {
      map['title'] = Variable<String>(title.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (audioPath.present) {
      map['audio_path'] = Variable<String>(audioPath.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    if (lastReviewedAt.present) {
      map['last_reviewed_at'] = Variable<String>(lastReviewedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LessonsCompanion(')
          ..write('id: $id, ')
          ..write('topicId: $topicId, ')
          ..write('orderIndex: $orderIndex, ')
          ..write('title: $title, ')
          ..write('status: $status, ')
          ..write('audioPath: $audioPath, ')
          ..write('createdAt: $createdAt, ')
          ..write('lastReviewedAt: $lastReviewedAt')
          ..write(')'))
        .toString();
  }
}

class $SentencesTable extends Sentences
    with TableInfo<$SentencesTable, Sentence> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SentencesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _lessonIdMeta = const VerificationMeta(
    'lessonId',
  );
  @override
  late final GeneratedColumn<int> lessonId = GeneratedColumn<int>(
    'lesson_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _paraIndexMeta = const VerificationMeta(
    'paraIndex',
  );
  @override
  late final GeneratedColumn<int> paraIndex = GeneratedColumn<int>(
    'para_index',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sentIndexMeta = const VerificationMeta(
    'sentIndex',
  );
  @override
  late final GeneratedColumn<int> sentIndex = GeneratedColumn<int>(
    'sent_index',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _contentMeta = const VerificationMeta(
    'content',
  );
  @override
  late final GeneratedColumn<String> content = GeneratedColumn<String>(
    'text',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _segmentationMeta = const VerificationMeta(
    'segmentation',
  );
  @override
  late final GeneratedColumn<String> segmentation = GeneratedColumn<String>(
    'segmentation',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _translationMeta = const VerificationMeta(
    'translation',
  );
  @override
  late final GeneratedColumn<String> translation = GeneratedColumn<String>(
    'translation',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    lessonId,
    paraIndex,
    sentIndex,
    content,
    segmentation,
    translation,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'sentences';
  @override
  VerificationContext validateIntegrity(
    Insertable<Sentence> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('lesson_id')) {
      context.handle(
        _lessonIdMeta,
        lessonId.isAcceptableOrUnknown(data['lesson_id']!, _lessonIdMeta),
      );
    } else if (isInserting) {
      context.missing(_lessonIdMeta);
    }
    if (data.containsKey('para_index')) {
      context.handle(
        _paraIndexMeta,
        paraIndex.isAcceptableOrUnknown(data['para_index']!, _paraIndexMeta),
      );
    } else if (isInserting) {
      context.missing(_paraIndexMeta);
    }
    if (data.containsKey('sent_index')) {
      context.handle(
        _sentIndexMeta,
        sentIndex.isAcceptableOrUnknown(data['sent_index']!, _sentIndexMeta),
      );
    } else if (isInserting) {
      context.missing(_sentIndexMeta);
    }
    if (data.containsKey('text')) {
      context.handle(
        _contentMeta,
        content.isAcceptableOrUnknown(data['text']!, _contentMeta),
      );
    } else if (isInserting) {
      context.missing(_contentMeta);
    }
    if (data.containsKey('segmentation')) {
      context.handle(
        _segmentationMeta,
        segmentation.isAcceptableOrUnknown(
          data['segmentation']!,
          _segmentationMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_segmentationMeta);
    }
    if (data.containsKey('translation')) {
      context.handle(
        _translationMeta,
        translation.isAcceptableOrUnknown(
          data['translation']!,
          _translationMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  Sentence map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Sentence(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      lessonId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}lesson_id'],
      )!,
      paraIndex: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}para_index'],
      )!,
      sentIndex: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}sent_index'],
      )!,
      content: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}text'],
      )!,
      segmentation: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}segmentation'],
      )!,
      translation: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}translation'],
      ),
    );
  }

  @override
  $SentencesTable createAlias(String alias) {
    return $SentencesTable(attachedDatabase, alias);
  }
}

class Sentence extends DataClass implements Insertable<Sentence> {
  final int id;
  final int lessonId;
  final int paraIndex;
  final int sentIndex;

  /// Unsegmented Chinese sentence text. (Getter is `content`, not `text`,
  /// because `text` would shadow drift's `text()` column builder.)
  final String content;

  /// JSON array of word tokens, imported as-is from the desktop bundle.
  final String segmentation;
  final String? translation;
  const Sentence({
    required this.id,
    required this.lessonId,
    required this.paraIndex,
    required this.sentIndex,
    required this.content,
    required this.segmentation,
    this.translation,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['lesson_id'] = Variable<int>(lessonId);
    map['para_index'] = Variable<int>(paraIndex);
    map['sent_index'] = Variable<int>(sentIndex);
    map['text'] = Variable<String>(content);
    map['segmentation'] = Variable<String>(segmentation);
    if (!nullToAbsent || translation != null) {
      map['translation'] = Variable<String>(translation);
    }
    return map;
  }

  SentencesCompanion toCompanion(bool nullToAbsent) {
    return SentencesCompanion(
      id: Value(id),
      lessonId: Value(lessonId),
      paraIndex: Value(paraIndex),
      sentIndex: Value(sentIndex),
      content: Value(content),
      segmentation: Value(segmentation),
      translation: translation == null && nullToAbsent
          ? const Value.absent()
          : Value(translation),
    );
  }

  factory Sentence.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Sentence(
      id: serializer.fromJson<int>(json['id']),
      lessonId: serializer.fromJson<int>(json['lessonId']),
      paraIndex: serializer.fromJson<int>(json['paraIndex']),
      sentIndex: serializer.fromJson<int>(json['sentIndex']),
      content: serializer.fromJson<String>(json['content']),
      segmentation: serializer.fromJson<String>(json['segmentation']),
      translation: serializer.fromJson<String?>(json['translation']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'lessonId': serializer.toJson<int>(lessonId),
      'paraIndex': serializer.toJson<int>(paraIndex),
      'sentIndex': serializer.toJson<int>(sentIndex),
      'content': serializer.toJson<String>(content),
      'segmentation': serializer.toJson<String>(segmentation),
      'translation': serializer.toJson<String?>(translation),
    };
  }

  Sentence copyWith({
    int? id,
    int? lessonId,
    int? paraIndex,
    int? sentIndex,
    String? content,
    String? segmentation,
    Value<String?> translation = const Value.absent(),
  }) => Sentence(
    id: id ?? this.id,
    lessonId: lessonId ?? this.lessonId,
    paraIndex: paraIndex ?? this.paraIndex,
    sentIndex: sentIndex ?? this.sentIndex,
    content: content ?? this.content,
    segmentation: segmentation ?? this.segmentation,
    translation: translation.present ? translation.value : this.translation,
  );
  Sentence copyWithCompanion(SentencesCompanion data) {
    return Sentence(
      id: data.id.present ? data.id.value : this.id,
      lessonId: data.lessonId.present ? data.lessonId.value : this.lessonId,
      paraIndex: data.paraIndex.present ? data.paraIndex.value : this.paraIndex,
      sentIndex: data.sentIndex.present ? data.sentIndex.value : this.sentIndex,
      content: data.content.present ? data.content.value : this.content,
      segmentation: data.segmentation.present
          ? data.segmentation.value
          : this.segmentation,
      translation: data.translation.present
          ? data.translation.value
          : this.translation,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Sentence(')
          ..write('id: $id, ')
          ..write('lessonId: $lessonId, ')
          ..write('paraIndex: $paraIndex, ')
          ..write('sentIndex: $sentIndex, ')
          ..write('content: $content, ')
          ..write('segmentation: $segmentation, ')
          ..write('translation: $translation')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    lessonId,
    paraIndex,
    sentIndex,
    content,
    segmentation,
    translation,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Sentence &&
          other.id == this.id &&
          other.lessonId == this.lessonId &&
          other.paraIndex == this.paraIndex &&
          other.sentIndex == this.sentIndex &&
          other.content == this.content &&
          other.segmentation == this.segmentation &&
          other.translation == this.translation);
}

class SentencesCompanion extends UpdateCompanion<Sentence> {
  final Value<int> id;
  final Value<int> lessonId;
  final Value<int> paraIndex;
  final Value<int> sentIndex;
  final Value<String> content;
  final Value<String> segmentation;
  final Value<String?> translation;
  const SentencesCompanion({
    this.id = const Value.absent(),
    this.lessonId = const Value.absent(),
    this.paraIndex = const Value.absent(),
    this.sentIndex = const Value.absent(),
    this.content = const Value.absent(),
    this.segmentation = const Value.absent(),
    this.translation = const Value.absent(),
  });
  SentencesCompanion.insert({
    this.id = const Value.absent(),
    required int lessonId,
    required int paraIndex,
    required int sentIndex,
    required String content,
    required String segmentation,
    this.translation = const Value.absent(),
  }) : lessonId = Value(lessonId),
       paraIndex = Value(paraIndex),
       sentIndex = Value(sentIndex),
       content = Value(content),
       segmentation = Value(segmentation);
  static Insertable<Sentence> custom({
    Expression<int>? id,
    Expression<int>? lessonId,
    Expression<int>? paraIndex,
    Expression<int>? sentIndex,
    Expression<String>? content,
    Expression<String>? segmentation,
    Expression<String>? translation,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (lessonId != null) 'lesson_id': lessonId,
      if (paraIndex != null) 'para_index': paraIndex,
      if (sentIndex != null) 'sent_index': sentIndex,
      if (content != null) 'text': content,
      if (segmentation != null) 'segmentation': segmentation,
      if (translation != null) 'translation': translation,
    });
  }

  SentencesCompanion copyWith({
    Value<int>? id,
    Value<int>? lessonId,
    Value<int>? paraIndex,
    Value<int>? sentIndex,
    Value<String>? content,
    Value<String>? segmentation,
    Value<String?>? translation,
  }) {
    return SentencesCompanion(
      id: id ?? this.id,
      lessonId: lessonId ?? this.lessonId,
      paraIndex: paraIndex ?? this.paraIndex,
      sentIndex: sentIndex ?? this.sentIndex,
      content: content ?? this.content,
      segmentation: segmentation ?? this.segmentation,
      translation: translation ?? this.translation,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (lessonId.present) {
      map['lesson_id'] = Variable<int>(lessonId.value);
    }
    if (paraIndex.present) {
      map['para_index'] = Variable<int>(paraIndex.value);
    }
    if (sentIndex.present) {
      map['sent_index'] = Variable<int>(sentIndex.value);
    }
    if (content.present) {
      map['text'] = Variable<String>(content.value);
    }
    if (segmentation.present) {
      map['segmentation'] = Variable<String>(segmentation.value);
    }
    if (translation.present) {
      map['translation'] = Variable<String>(translation.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SentencesCompanion(')
          ..write('id: $id, ')
          ..write('lessonId: $lessonId, ')
          ..write('paraIndex: $paraIndex, ')
          ..write('sentIndex: $sentIndex, ')
          ..write('content: $content, ')
          ..write('segmentation: $segmentation, ')
          ..write('translation: $translation')
          ..write(')'))
        .toString();
  }
}

class $WordsTable extends Words with TableInfo<$WordsTable, Word> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $WordsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _wordMeta = const VerificationMeta('word');
  @override
  late final GeneratedColumn<String> word = GeneratedColumn<String>(
    'text',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _pinyinMeta = const VerificationMeta('pinyin');
  @override
  late final GeneratedColumn<String> pinyin = GeneratedColumn<String>(
    'pinyin',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _definitionMeta = const VerificationMeta(
    'definition',
  );
  @override
  late final GeneratedColumn<String> definition = GeneratedColumn<String>(
    'definition',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _listStateMeta = const VerificationMeta(
    'listState',
  );
  @override
  late final GeneratedColumn<String> listState = GeneratedColumn<String>(
    'list_state',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _hskWordIdMeta = const VerificationMeta(
    'hskWordId',
  );
  @override
  late final GeneratedColumn<int> hskWordId = GeneratedColumn<int>(
    'hsk_word_id',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _sourceMeta = const VerificationMeta('source');
  @override
  late final GeneratedColumn<String> source = GeneratedColumn<String>(
    'source',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _addedAtMeta = const VerificationMeta(
    'addedAt',
  );
  @override
  late final GeneratedColumn<String> addedAt = GeneratedColumn<String>(
    'added_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _easeMeta = const VerificationMeta('ease');
  @override
  late final GeneratedColumn<double> ease = GeneratedColumn<double>(
    'ease',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
    defaultValue: const Constant(2.5),
  );
  static const VerificationMeta _intervalDaysMeta = const VerificationMeta(
    'intervalDays',
  );
  @override
  late final GeneratedColumn<double> intervalDays = GeneratedColumn<double>(
    'interval_days',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _dueAtMeta = const VerificationMeta('dueAt');
  @override
  late final GeneratedColumn<String> dueAt = GeneratedColumn<String>(
    'due_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _repsMeta = const VerificationMeta('reps');
  @override
  late final GeneratedColumn<int> reps = GeneratedColumn<int>(
    'reps',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _lapsesMeta = const VerificationMeta('lapses');
  @override
  late final GeneratedColumn<int> lapses = GeneratedColumn<int>(
    'lapses',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _lastRatedAtMeta = const VerificationMeta(
    'lastRatedAt',
  );
  @override
  late final GeneratedColumn<String> lastRatedAt = GeneratedColumn<String>(
    'last_rated_at',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    word,
    pinyin,
    definition,
    listState,
    hskWordId,
    source,
    addedAt,
    ease,
    intervalDays,
    dueAt,
    reps,
    lapses,
    lastRatedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'words';
  @override
  VerificationContext validateIntegrity(
    Insertable<Word> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('text')) {
      context.handle(
        _wordMeta,
        word.isAcceptableOrUnknown(data['text']!, _wordMeta),
      );
    } else if (isInserting) {
      context.missing(_wordMeta);
    }
    if (data.containsKey('pinyin')) {
      context.handle(
        _pinyinMeta,
        pinyin.isAcceptableOrUnknown(data['pinyin']!, _pinyinMeta),
      );
    }
    if (data.containsKey('definition')) {
      context.handle(
        _definitionMeta,
        definition.isAcceptableOrUnknown(data['definition']!, _definitionMeta),
      );
    }
    if (data.containsKey('list_state')) {
      context.handle(
        _listStateMeta,
        listState.isAcceptableOrUnknown(data['list_state']!, _listStateMeta),
      );
    } else if (isInserting) {
      context.missing(_listStateMeta);
    }
    if (data.containsKey('hsk_word_id')) {
      context.handle(
        _hskWordIdMeta,
        hskWordId.isAcceptableOrUnknown(data['hsk_word_id']!, _hskWordIdMeta),
      );
    }
    if (data.containsKey('source')) {
      context.handle(
        _sourceMeta,
        source.isAcceptableOrUnknown(data['source']!, _sourceMeta),
      );
    } else if (isInserting) {
      context.missing(_sourceMeta);
    }
    if (data.containsKey('added_at')) {
      context.handle(
        _addedAtMeta,
        addedAt.isAcceptableOrUnknown(data['added_at']!, _addedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_addedAtMeta);
    }
    if (data.containsKey('ease')) {
      context.handle(
        _easeMeta,
        ease.isAcceptableOrUnknown(data['ease']!, _easeMeta),
      );
    }
    if (data.containsKey('interval_days')) {
      context.handle(
        _intervalDaysMeta,
        intervalDays.isAcceptableOrUnknown(
          data['interval_days']!,
          _intervalDaysMeta,
        ),
      );
    }
    if (data.containsKey('due_at')) {
      context.handle(
        _dueAtMeta,
        dueAt.isAcceptableOrUnknown(data['due_at']!, _dueAtMeta),
      );
    }
    if (data.containsKey('reps')) {
      context.handle(
        _repsMeta,
        reps.isAcceptableOrUnknown(data['reps']!, _repsMeta),
      );
    }
    if (data.containsKey('lapses')) {
      context.handle(
        _lapsesMeta,
        lapses.isAcceptableOrUnknown(data['lapses']!, _lapsesMeta),
      );
    }
    if (data.containsKey('last_rated_at')) {
      context.handle(
        _lastRatedAtMeta,
        lastRatedAt.isAcceptableOrUnknown(
          data['last_rated_at']!,
          _lastRatedAtMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  Word map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Word(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      word: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}text'],
      )!,
      pinyin: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}pinyin'],
      ),
      definition: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}definition'],
      ),
      listState: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}list_state'],
      )!,
      hskWordId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}hsk_word_id'],
      ),
      source: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source'],
      )!,
      addedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}added_at'],
      )!,
      ease: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}ease'],
      )!,
      intervalDays: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}interval_days'],
      ),
      dueAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}due_at'],
      ),
      reps: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}reps'],
      )!,
      lapses: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}lapses'],
      )!,
      lastRatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}last_rated_at'],
      ),
    );
  }

  @override
  $WordsTable createAlias(String alias) {
    return $WordsTable(attachedDatabase, alias);
  }
}

class Word extends DataClass implements Insertable<Word> {
  /// Desktop word ids on import; locally created words (unlisted words the
  /// user added from a popup) get fresh auto ids — replaced on next import.
  final int id;

  /// The word's written form (SQL column `text`; getter is `word` because
  /// `text` would shadow drift's `text()` column builder).
  final String word;
  final String? pinyin;
  final String? definition;

  /// new | learned | basic
  final String listState;
  final int? hskWordId;
  final String source;
  final String addedAt;
  final double ease;
  final double? intervalDays;
  final String? dueAt;
  final int reps;
  final int lapses;
  final String? lastRatedAt;
  const Word({
    required this.id,
    required this.word,
    this.pinyin,
    this.definition,
    required this.listState,
    this.hskWordId,
    required this.source,
    required this.addedAt,
    required this.ease,
    this.intervalDays,
    this.dueAt,
    required this.reps,
    required this.lapses,
    this.lastRatedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['text'] = Variable<String>(word);
    if (!nullToAbsent || pinyin != null) {
      map['pinyin'] = Variable<String>(pinyin);
    }
    if (!nullToAbsent || definition != null) {
      map['definition'] = Variable<String>(definition);
    }
    map['list_state'] = Variable<String>(listState);
    if (!nullToAbsent || hskWordId != null) {
      map['hsk_word_id'] = Variable<int>(hskWordId);
    }
    map['source'] = Variable<String>(source);
    map['added_at'] = Variable<String>(addedAt);
    map['ease'] = Variable<double>(ease);
    if (!nullToAbsent || intervalDays != null) {
      map['interval_days'] = Variable<double>(intervalDays);
    }
    if (!nullToAbsent || dueAt != null) {
      map['due_at'] = Variable<String>(dueAt);
    }
    map['reps'] = Variable<int>(reps);
    map['lapses'] = Variable<int>(lapses);
    if (!nullToAbsent || lastRatedAt != null) {
      map['last_rated_at'] = Variable<String>(lastRatedAt);
    }
    return map;
  }

  WordsCompanion toCompanion(bool nullToAbsent) {
    return WordsCompanion(
      id: Value(id),
      word: Value(word),
      pinyin: pinyin == null && nullToAbsent
          ? const Value.absent()
          : Value(pinyin),
      definition: definition == null && nullToAbsent
          ? const Value.absent()
          : Value(definition),
      listState: Value(listState),
      hskWordId: hskWordId == null && nullToAbsent
          ? const Value.absent()
          : Value(hskWordId),
      source: Value(source),
      addedAt: Value(addedAt),
      ease: Value(ease),
      intervalDays: intervalDays == null && nullToAbsent
          ? const Value.absent()
          : Value(intervalDays),
      dueAt: dueAt == null && nullToAbsent
          ? const Value.absent()
          : Value(dueAt),
      reps: Value(reps),
      lapses: Value(lapses),
      lastRatedAt: lastRatedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(lastRatedAt),
    );
  }

  factory Word.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Word(
      id: serializer.fromJson<int>(json['id']),
      word: serializer.fromJson<String>(json['word']),
      pinyin: serializer.fromJson<String?>(json['pinyin']),
      definition: serializer.fromJson<String?>(json['definition']),
      listState: serializer.fromJson<String>(json['listState']),
      hskWordId: serializer.fromJson<int?>(json['hskWordId']),
      source: serializer.fromJson<String>(json['source']),
      addedAt: serializer.fromJson<String>(json['addedAt']),
      ease: serializer.fromJson<double>(json['ease']),
      intervalDays: serializer.fromJson<double?>(json['intervalDays']),
      dueAt: serializer.fromJson<String?>(json['dueAt']),
      reps: serializer.fromJson<int>(json['reps']),
      lapses: serializer.fromJson<int>(json['lapses']),
      lastRatedAt: serializer.fromJson<String?>(json['lastRatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'word': serializer.toJson<String>(word),
      'pinyin': serializer.toJson<String?>(pinyin),
      'definition': serializer.toJson<String?>(definition),
      'listState': serializer.toJson<String>(listState),
      'hskWordId': serializer.toJson<int?>(hskWordId),
      'source': serializer.toJson<String>(source),
      'addedAt': serializer.toJson<String>(addedAt),
      'ease': serializer.toJson<double>(ease),
      'intervalDays': serializer.toJson<double?>(intervalDays),
      'dueAt': serializer.toJson<String?>(dueAt),
      'reps': serializer.toJson<int>(reps),
      'lapses': serializer.toJson<int>(lapses),
      'lastRatedAt': serializer.toJson<String?>(lastRatedAt),
    };
  }

  Word copyWith({
    int? id,
    String? word,
    Value<String?> pinyin = const Value.absent(),
    Value<String?> definition = const Value.absent(),
    String? listState,
    Value<int?> hskWordId = const Value.absent(),
    String? source,
    String? addedAt,
    double? ease,
    Value<double?> intervalDays = const Value.absent(),
    Value<String?> dueAt = const Value.absent(),
    int? reps,
    int? lapses,
    Value<String?> lastRatedAt = const Value.absent(),
  }) => Word(
    id: id ?? this.id,
    word: word ?? this.word,
    pinyin: pinyin.present ? pinyin.value : this.pinyin,
    definition: definition.present ? definition.value : this.definition,
    listState: listState ?? this.listState,
    hskWordId: hskWordId.present ? hskWordId.value : this.hskWordId,
    source: source ?? this.source,
    addedAt: addedAt ?? this.addedAt,
    ease: ease ?? this.ease,
    intervalDays: intervalDays.present ? intervalDays.value : this.intervalDays,
    dueAt: dueAt.present ? dueAt.value : this.dueAt,
    reps: reps ?? this.reps,
    lapses: lapses ?? this.lapses,
    lastRatedAt: lastRatedAt.present ? lastRatedAt.value : this.lastRatedAt,
  );
  Word copyWithCompanion(WordsCompanion data) {
    return Word(
      id: data.id.present ? data.id.value : this.id,
      word: data.word.present ? data.word.value : this.word,
      pinyin: data.pinyin.present ? data.pinyin.value : this.pinyin,
      definition: data.definition.present
          ? data.definition.value
          : this.definition,
      listState: data.listState.present ? data.listState.value : this.listState,
      hskWordId: data.hskWordId.present ? data.hskWordId.value : this.hskWordId,
      source: data.source.present ? data.source.value : this.source,
      addedAt: data.addedAt.present ? data.addedAt.value : this.addedAt,
      ease: data.ease.present ? data.ease.value : this.ease,
      intervalDays: data.intervalDays.present
          ? data.intervalDays.value
          : this.intervalDays,
      dueAt: data.dueAt.present ? data.dueAt.value : this.dueAt,
      reps: data.reps.present ? data.reps.value : this.reps,
      lapses: data.lapses.present ? data.lapses.value : this.lapses,
      lastRatedAt: data.lastRatedAt.present
          ? data.lastRatedAt.value
          : this.lastRatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Word(')
          ..write('id: $id, ')
          ..write('word: $word, ')
          ..write('pinyin: $pinyin, ')
          ..write('definition: $definition, ')
          ..write('listState: $listState, ')
          ..write('hskWordId: $hskWordId, ')
          ..write('source: $source, ')
          ..write('addedAt: $addedAt, ')
          ..write('ease: $ease, ')
          ..write('intervalDays: $intervalDays, ')
          ..write('dueAt: $dueAt, ')
          ..write('reps: $reps, ')
          ..write('lapses: $lapses, ')
          ..write('lastRatedAt: $lastRatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    word,
    pinyin,
    definition,
    listState,
    hskWordId,
    source,
    addedAt,
    ease,
    intervalDays,
    dueAt,
    reps,
    lapses,
    lastRatedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Word &&
          other.id == this.id &&
          other.word == this.word &&
          other.pinyin == this.pinyin &&
          other.definition == this.definition &&
          other.listState == this.listState &&
          other.hskWordId == this.hskWordId &&
          other.source == this.source &&
          other.addedAt == this.addedAt &&
          other.ease == this.ease &&
          other.intervalDays == this.intervalDays &&
          other.dueAt == this.dueAt &&
          other.reps == this.reps &&
          other.lapses == this.lapses &&
          other.lastRatedAt == this.lastRatedAt);
}

class WordsCompanion extends UpdateCompanion<Word> {
  final Value<int> id;
  final Value<String> word;
  final Value<String?> pinyin;
  final Value<String?> definition;
  final Value<String> listState;
  final Value<int?> hskWordId;
  final Value<String> source;
  final Value<String> addedAt;
  final Value<double> ease;
  final Value<double?> intervalDays;
  final Value<String?> dueAt;
  final Value<int> reps;
  final Value<int> lapses;
  final Value<String?> lastRatedAt;
  const WordsCompanion({
    this.id = const Value.absent(),
    this.word = const Value.absent(),
    this.pinyin = const Value.absent(),
    this.definition = const Value.absent(),
    this.listState = const Value.absent(),
    this.hskWordId = const Value.absent(),
    this.source = const Value.absent(),
    this.addedAt = const Value.absent(),
    this.ease = const Value.absent(),
    this.intervalDays = const Value.absent(),
    this.dueAt = const Value.absent(),
    this.reps = const Value.absent(),
    this.lapses = const Value.absent(),
    this.lastRatedAt = const Value.absent(),
  });
  WordsCompanion.insert({
    this.id = const Value.absent(),
    required String word,
    this.pinyin = const Value.absent(),
    this.definition = const Value.absent(),
    required String listState,
    this.hskWordId = const Value.absent(),
    required String source,
    required String addedAt,
    this.ease = const Value.absent(),
    this.intervalDays = const Value.absent(),
    this.dueAt = const Value.absent(),
    this.reps = const Value.absent(),
    this.lapses = const Value.absent(),
    this.lastRatedAt = const Value.absent(),
  }) : word = Value(word),
       listState = Value(listState),
       source = Value(source),
       addedAt = Value(addedAt);
  static Insertable<Word> custom({
    Expression<int>? id,
    Expression<String>? word,
    Expression<String>? pinyin,
    Expression<String>? definition,
    Expression<String>? listState,
    Expression<int>? hskWordId,
    Expression<String>? source,
    Expression<String>? addedAt,
    Expression<double>? ease,
    Expression<double>? intervalDays,
    Expression<String>? dueAt,
    Expression<int>? reps,
    Expression<int>? lapses,
    Expression<String>? lastRatedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (word != null) 'text': word,
      if (pinyin != null) 'pinyin': pinyin,
      if (definition != null) 'definition': definition,
      if (listState != null) 'list_state': listState,
      if (hskWordId != null) 'hsk_word_id': hskWordId,
      if (source != null) 'source': source,
      if (addedAt != null) 'added_at': addedAt,
      if (ease != null) 'ease': ease,
      if (intervalDays != null) 'interval_days': intervalDays,
      if (dueAt != null) 'due_at': dueAt,
      if (reps != null) 'reps': reps,
      if (lapses != null) 'lapses': lapses,
      if (lastRatedAt != null) 'last_rated_at': lastRatedAt,
    });
  }

  WordsCompanion copyWith({
    Value<int>? id,
    Value<String>? word,
    Value<String?>? pinyin,
    Value<String?>? definition,
    Value<String>? listState,
    Value<int?>? hskWordId,
    Value<String>? source,
    Value<String>? addedAt,
    Value<double>? ease,
    Value<double?>? intervalDays,
    Value<String?>? dueAt,
    Value<int>? reps,
    Value<int>? lapses,
    Value<String?>? lastRatedAt,
  }) {
    return WordsCompanion(
      id: id ?? this.id,
      word: word ?? this.word,
      pinyin: pinyin ?? this.pinyin,
      definition: definition ?? this.definition,
      listState: listState ?? this.listState,
      hskWordId: hskWordId ?? this.hskWordId,
      source: source ?? this.source,
      addedAt: addedAt ?? this.addedAt,
      ease: ease ?? this.ease,
      intervalDays: intervalDays ?? this.intervalDays,
      dueAt: dueAt ?? this.dueAt,
      reps: reps ?? this.reps,
      lapses: lapses ?? this.lapses,
      lastRatedAt: lastRatedAt ?? this.lastRatedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (word.present) {
      map['text'] = Variable<String>(word.value);
    }
    if (pinyin.present) {
      map['pinyin'] = Variable<String>(pinyin.value);
    }
    if (definition.present) {
      map['definition'] = Variable<String>(definition.value);
    }
    if (listState.present) {
      map['list_state'] = Variable<String>(listState.value);
    }
    if (hskWordId.present) {
      map['hsk_word_id'] = Variable<int>(hskWordId.value);
    }
    if (source.present) {
      map['source'] = Variable<String>(source.value);
    }
    if (addedAt.present) {
      map['added_at'] = Variable<String>(addedAt.value);
    }
    if (ease.present) {
      map['ease'] = Variable<double>(ease.value);
    }
    if (intervalDays.present) {
      map['interval_days'] = Variable<double>(intervalDays.value);
    }
    if (dueAt.present) {
      map['due_at'] = Variable<String>(dueAt.value);
    }
    if (reps.present) {
      map['reps'] = Variable<int>(reps.value);
    }
    if (lapses.present) {
      map['lapses'] = Variable<int>(lapses.value);
    }
    if (lastRatedAt.present) {
      map['last_rated_at'] = Variable<String>(lastRatedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('WordsCompanion(')
          ..write('id: $id, ')
          ..write('word: $word, ')
          ..write('pinyin: $pinyin, ')
          ..write('definition: $definition, ')
          ..write('listState: $listState, ')
          ..write('hskWordId: $hskWordId, ')
          ..write('source: $source, ')
          ..write('addedAt: $addedAt, ')
          ..write('ease: $ease, ')
          ..write('intervalDays: $intervalDays, ')
          ..write('dueAt: $dueAt, ')
          ..write('reps: $reps, ')
          ..write('lapses: $lapses, ')
          ..write('lastRatedAt: $lastRatedAt')
          ..write(')'))
        .toString();
  }
}

class $LessonWordsTable extends LessonWords
    with TableInfo<$LessonWordsTable, LessonWord> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LessonWordsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _lessonIdMeta = const VerificationMeta(
    'lessonId',
  );
  @override
  late final GeneratedColumn<int> lessonId = GeneratedColumn<int>(
    'lesson_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _wordIdMeta = const VerificationMeta('wordId');
  @override
  late final GeneratedColumn<int> wordId = GeneratedColumn<int>(
    'word_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _roleMeta = const VerificationMeta('role');
  @override
  late final GeneratedColumn<String> role = GeneratedColumn<String>(
    'role',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [lessonId, wordId, role];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'lesson_words';
  @override
  VerificationContext validateIntegrity(
    Insertable<LessonWord> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('lesson_id')) {
      context.handle(
        _lessonIdMeta,
        lessonId.isAcceptableOrUnknown(data['lesson_id']!, _lessonIdMeta),
      );
    } else if (isInserting) {
      context.missing(_lessonIdMeta);
    }
    if (data.containsKey('word_id')) {
      context.handle(
        _wordIdMeta,
        wordId.isAcceptableOrUnknown(data['word_id']!, _wordIdMeta),
      );
    } else if (isInserting) {
      context.missing(_wordIdMeta);
    }
    if (data.containsKey('role')) {
      context.handle(
        _roleMeta,
        role.isAcceptableOrUnknown(data['role']!, _roleMeta),
      );
    } else if (isInserting) {
      context.missing(_roleMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {lessonId, wordId};
  @override
  LessonWord map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return LessonWord(
      lessonId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}lesson_id'],
      )!,
      wordId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}word_id'],
      )!,
      role: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}role'],
      )!,
    );
  }

  @override
  $LessonWordsTable createAlias(String alias) {
    return $LessonWordsTable(attachedDatabase, alias);
  }
}

class LessonWord extends DataClass implements Insertable<LessonWord> {
  final int lessonId;
  final int wordId;

  /// new | review
  final String role;
  const LessonWord({
    required this.lessonId,
    required this.wordId,
    required this.role,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['lesson_id'] = Variable<int>(lessonId);
    map['word_id'] = Variable<int>(wordId);
    map['role'] = Variable<String>(role);
    return map;
  }

  LessonWordsCompanion toCompanion(bool nullToAbsent) {
    return LessonWordsCompanion(
      lessonId: Value(lessonId),
      wordId: Value(wordId),
      role: Value(role),
    );
  }

  factory LessonWord.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return LessonWord(
      lessonId: serializer.fromJson<int>(json['lessonId']),
      wordId: serializer.fromJson<int>(json['wordId']),
      role: serializer.fromJson<String>(json['role']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'lessonId': serializer.toJson<int>(lessonId),
      'wordId': serializer.toJson<int>(wordId),
      'role': serializer.toJson<String>(role),
    };
  }

  LessonWord copyWith({int? lessonId, int? wordId, String? role}) => LessonWord(
    lessonId: lessonId ?? this.lessonId,
    wordId: wordId ?? this.wordId,
    role: role ?? this.role,
  );
  LessonWord copyWithCompanion(LessonWordsCompanion data) {
    return LessonWord(
      lessonId: data.lessonId.present ? data.lessonId.value : this.lessonId,
      wordId: data.wordId.present ? data.wordId.value : this.wordId,
      role: data.role.present ? data.role.value : this.role,
    );
  }

  @override
  String toString() {
    return (StringBuffer('LessonWord(')
          ..write('lessonId: $lessonId, ')
          ..write('wordId: $wordId, ')
          ..write('role: $role')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(lessonId, wordId, role);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is LessonWord &&
          other.lessonId == this.lessonId &&
          other.wordId == this.wordId &&
          other.role == this.role);
}

class LessonWordsCompanion extends UpdateCompanion<LessonWord> {
  final Value<int> lessonId;
  final Value<int> wordId;
  final Value<String> role;
  final Value<int> rowid;
  const LessonWordsCompanion({
    this.lessonId = const Value.absent(),
    this.wordId = const Value.absent(),
    this.role = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  LessonWordsCompanion.insert({
    required int lessonId,
    required int wordId,
    required String role,
    this.rowid = const Value.absent(),
  }) : lessonId = Value(lessonId),
       wordId = Value(wordId),
       role = Value(role);
  static Insertable<LessonWord> custom({
    Expression<int>? lessonId,
    Expression<int>? wordId,
    Expression<String>? role,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (lessonId != null) 'lesson_id': lessonId,
      if (wordId != null) 'word_id': wordId,
      if (role != null) 'role': role,
      if (rowid != null) 'rowid': rowid,
    });
  }

  LessonWordsCompanion copyWith({
    Value<int>? lessonId,
    Value<int>? wordId,
    Value<String>? role,
    Value<int>? rowid,
  }) {
    return LessonWordsCompanion(
      lessonId: lessonId ?? this.lessonId,
      wordId: wordId ?? this.wordId,
      role: role ?? this.role,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (lessonId.present) {
      map['lesson_id'] = Variable<int>(lessonId.value);
    }
    if (wordId.present) {
      map['word_id'] = Variable<int>(wordId.value);
    }
    if (role.present) {
      map['role'] = Variable<String>(role.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LessonWordsCompanion(')
          ..write('lessonId: $lessonId, ')
          ..write('wordId: $wordId, ')
          ..write('role: $role, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $HskWordsTable extends HskWords with TableInfo<$HskWordsTable, HskWord> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $HskWordsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _wordMeta = const VerificationMeta('word');
  @override
  late final GeneratedColumn<String> word = GeneratedColumn<String>(
    'text',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _pinyinMeta = const VerificationMeta('pinyin');
  @override
  late final GeneratedColumn<String> pinyin = GeneratedColumn<String>(
    'pinyin',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _definitionMeta = const VerificationMeta(
    'definition',
  );
  @override
  late final GeneratedColumn<String> definition = GeneratedColumn<String>(
    'definition',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _levelMeta = const VerificationMeta('level');
  @override
  late final GeneratedColumn<int> level = GeneratedColumn<int>(
    'level',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _appStateMeta = const VerificationMeta(
    'appState',
  );
  @override
  late final GeneratedColumn<String> appState = GeneratedColumn<String>(
    'app_state',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    word,
    pinyin,
    definition,
    level,
    appState,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'hsk_words';
  @override
  VerificationContext validateIntegrity(
    Insertable<HskWord> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('text')) {
      context.handle(
        _wordMeta,
        word.isAcceptableOrUnknown(data['text']!, _wordMeta),
      );
    } else if (isInserting) {
      context.missing(_wordMeta);
    }
    if (data.containsKey('pinyin')) {
      context.handle(
        _pinyinMeta,
        pinyin.isAcceptableOrUnknown(data['pinyin']!, _pinyinMeta),
      );
    }
    if (data.containsKey('definition')) {
      context.handle(
        _definitionMeta,
        definition.isAcceptableOrUnknown(data['definition']!, _definitionMeta),
      );
    }
    if (data.containsKey('level')) {
      context.handle(
        _levelMeta,
        level.isAcceptableOrUnknown(data['level']!, _levelMeta),
      );
    } else if (isInserting) {
      context.missing(_levelMeta);
    }
    if (data.containsKey('app_state')) {
      context.handle(
        _appStateMeta,
        appState.isAcceptableOrUnknown(data['app_state']!, _appStateMeta),
      );
    } else if (isInserting) {
      context.missing(_appStateMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  HskWord map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return HskWord(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      word: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}text'],
      )!,
      pinyin: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}pinyin'],
      ),
      definition: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}definition'],
      ),
      level: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}level'],
      )!,
      appState: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}app_state'],
      )!,
    );
  }

  @override
  $HskWordsTable createAlias(String alias) {
    return $HskWordsTable(attachedDatabase, alias);
  }
}

class HskWord extends DataClass implements Insertable<HskWord> {
  final int id;

  /// The word's written form (SQL column `text`; getter is `word` because
  /// `text` would shadow drift's `text()` column builder).
  final String word;
  final String? pinyin;
  final String? definition;
  final int level;

  /// unused | new | basic | learned
  final String appState;
  const HskWord({
    required this.id,
    required this.word,
    this.pinyin,
    this.definition,
    required this.level,
    required this.appState,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['text'] = Variable<String>(word);
    if (!nullToAbsent || pinyin != null) {
      map['pinyin'] = Variable<String>(pinyin);
    }
    if (!nullToAbsent || definition != null) {
      map['definition'] = Variable<String>(definition);
    }
    map['level'] = Variable<int>(level);
    map['app_state'] = Variable<String>(appState);
    return map;
  }

  HskWordsCompanion toCompanion(bool nullToAbsent) {
    return HskWordsCompanion(
      id: Value(id),
      word: Value(word),
      pinyin: pinyin == null && nullToAbsent
          ? const Value.absent()
          : Value(pinyin),
      definition: definition == null && nullToAbsent
          ? const Value.absent()
          : Value(definition),
      level: Value(level),
      appState: Value(appState),
    );
  }

  factory HskWord.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return HskWord(
      id: serializer.fromJson<int>(json['id']),
      word: serializer.fromJson<String>(json['word']),
      pinyin: serializer.fromJson<String?>(json['pinyin']),
      definition: serializer.fromJson<String?>(json['definition']),
      level: serializer.fromJson<int>(json['level']),
      appState: serializer.fromJson<String>(json['appState']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'word': serializer.toJson<String>(word),
      'pinyin': serializer.toJson<String?>(pinyin),
      'definition': serializer.toJson<String?>(definition),
      'level': serializer.toJson<int>(level),
      'appState': serializer.toJson<String>(appState),
    };
  }

  HskWord copyWith({
    int? id,
    String? word,
    Value<String?> pinyin = const Value.absent(),
    Value<String?> definition = const Value.absent(),
    int? level,
    String? appState,
  }) => HskWord(
    id: id ?? this.id,
    word: word ?? this.word,
    pinyin: pinyin.present ? pinyin.value : this.pinyin,
    definition: definition.present ? definition.value : this.definition,
    level: level ?? this.level,
    appState: appState ?? this.appState,
  );
  HskWord copyWithCompanion(HskWordsCompanion data) {
    return HskWord(
      id: data.id.present ? data.id.value : this.id,
      word: data.word.present ? data.word.value : this.word,
      pinyin: data.pinyin.present ? data.pinyin.value : this.pinyin,
      definition: data.definition.present
          ? data.definition.value
          : this.definition,
      level: data.level.present ? data.level.value : this.level,
      appState: data.appState.present ? data.appState.value : this.appState,
    );
  }

  @override
  String toString() {
    return (StringBuffer('HskWord(')
          ..write('id: $id, ')
          ..write('word: $word, ')
          ..write('pinyin: $pinyin, ')
          ..write('definition: $definition, ')
          ..write('level: $level, ')
          ..write('appState: $appState')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, word, pinyin, definition, level, appState);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is HskWord &&
          other.id == this.id &&
          other.word == this.word &&
          other.pinyin == this.pinyin &&
          other.definition == this.definition &&
          other.level == this.level &&
          other.appState == this.appState);
}

class HskWordsCompanion extends UpdateCompanion<HskWord> {
  final Value<int> id;
  final Value<String> word;
  final Value<String?> pinyin;
  final Value<String?> definition;
  final Value<int> level;
  final Value<String> appState;
  const HskWordsCompanion({
    this.id = const Value.absent(),
    this.word = const Value.absent(),
    this.pinyin = const Value.absent(),
    this.definition = const Value.absent(),
    this.level = const Value.absent(),
    this.appState = const Value.absent(),
  });
  HskWordsCompanion.insert({
    this.id = const Value.absent(),
    required String word,
    this.pinyin = const Value.absent(),
    this.definition = const Value.absent(),
    required int level,
    required String appState,
  }) : word = Value(word),
       level = Value(level),
       appState = Value(appState);
  static Insertable<HskWord> custom({
    Expression<int>? id,
    Expression<String>? word,
    Expression<String>? pinyin,
    Expression<String>? definition,
    Expression<int>? level,
    Expression<String>? appState,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (word != null) 'text': word,
      if (pinyin != null) 'pinyin': pinyin,
      if (definition != null) 'definition': definition,
      if (level != null) 'level': level,
      if (appState != null) 'app_state': appState,
    });
  }

  HskWordsCompanion copyWith({
    Value<int>? id,
    Value<String>? word,
    Value<String?>? pinyin,
    Value<String?>? definition,
    Value<int>? level,
    Value<String>? appState,
  }) {
    return HskWordsCompanion(
      id: id ?? this.id,
      word: word ?? this.word,
      pinyin: pinyin ?? this.pinyin,
      definition: definition ?? this.definition,
      level: level ?? this.level,
      appState: appState ?? this.appState,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (word.present) {
      map['text'] = Variable<String>(word.value);
    }
    if (pinyin.present) {
      map['pinyin'] = Variable<String>(pinyin.value);
    }
    if (definition.present) {
      map['definition'] = Variable<String>(definition.value);
    }
    if (level.present) {
      map['level'] = Variable<int>(level.value);
    }
    if (appState.present) {
      map['app_state'] = Variable<String>(appState.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('HskWordsCompanion(')
          ..write('id: $id, ')
          ..write('word: $word, ')
          ..write('pinyin: $pinyin, ')
          ..write('definition: $definition, ')
          ..write('level: $level, ')
          ..write('appState: $appState')
          ..write(')'))
        .toString();
  }
}

class $PendingEventsTable extends PendingEvents
    with TableInfo<$PendingEventsTable, PendingEvent> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $PendingEventsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _typeMeta = const VerificationMeta('type');
  @override
  late final GeneratedColumn<String> type = GeneratedColumn<String>(
    'type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _payloadMeta = const VerificationMeta(
    'payload',
  );
  @override
  late final GeneratedColumn<String> payload = GeneratedColumn<String>(
    'payload',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [id, type, payload, createdAt];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'pending_events';
  @override
  VerificationContext validateIntegrity(
    Insertable<PendingEvent> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('type')) {
      context.handle(
        _typeMeta,
        type.isAcceptableOrUnknown(data['type']!, _typeMeta),
      );
    } else if (isInserting) {
      context.missing(_typeMeta);
    }
    if (data.containsKey('payload')) {
      context.handle(
        _payloadMeta,
        payload.isAcceptableOrUnknown(data['payload']!, _payloadMeta),
      );
    } else if (isInserting) {
      context.missing(_payloadMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  PendingEvent map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return PendingEvent(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      type: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}type'],
      )!,
      payload: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}payload'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $PendingEventsTable createAlias(String alias) {
    return $PendingEventsTable(attachedDatabase, alias);
  }
}

class PendingEvent extends DataClass implements Insertable<PendingEvent> {
  final int id;

  /// rating | lesson_reviewed | word_action
  final String type;

  /// The full event record as JSON (exactly what goes into events.jsonl).
  final String payload;
  final String createdAt;
  const PendingEvent({
    required this.id,
    required this.type,
    required this.payload,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['type'] = Variable<String>(type);
    map['payload'] = Variable<String>(payload);
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  PendingEventsCompanion toCompanion(bool nullToAbsent) {
    return PendingEventsCompanion(
      id: Value(id),
      type: Value(type),
      payload: Value(payload),
      createdAt: Value(createdAt),
    );
  }

  factory PendingEvent.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return PendingEvent(
      id: serializer.fromJson<int>(json['id']),
      type: serializer.fromJson<String>(json['type']),
      payload: serializer.fromJson<String>(json['payload']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'type': serializer.toJson<String>(type),
      'payload': serializer.toJson<String>(payload),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  PendingEvent copyWith({
    int? id,
    String? type,
    String? payload,
    String? createdAt,
  }) => PendingEvent(
    id: id ?? this.id,
    type: type ?? this.type,
    payload: payload ?? this.payload,
    createdAt: createdAt ?? this.createdAt,
  );
  PendingEvent copyWithCompanion(PendingEventsCompanion data) {
    return PendingEvent(
      id: data.id.present ? data.id.value : this.id,
      type: data.type.present ? data.type.value : this.type,
      payload: data.payload.present ? data.payload.value : this.payload,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('PendingEvent(')
          ..write('id: $id, ')
          ..write('type: $type, ')
          ..write('payload: $payload, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(id, type, payload, createdAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is PendingEvent &&
          other.id == this.id &&
          other.type == this.type &&
          other.payload == this.payload &&
          other.createdAt == this.createdAt);
}

class PendingEventsCompanion extends UpdateCompanion<PendingEvent> {
  final Value<int> id;
  final Value<String> type;
  final Value<String> payload;
  final Value<String> createdAt;
  const PendingEventsCompanion({
    this.id = const Value.absent(),
    this.type = const Value.absent(),
    this.payload = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  PendingEventsCompanion.insert({
    this.id = const Value.absent(),
    required String type,
    required String payload,
    required String createdAt,
  }) : type = Value(type),
       payload = Value(payload),
       createdAt = Value(createdAt);
  static Insertable<PendingEvent> custom({
    Expression<int>? id,
    Expression<String>? type,
    Expression<String>? payload,
    Expression<String>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (type != null) 'type': type,
      if (payload != null) 'payload': payload,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  PendingEventsCompanion copyWith({
    Value<int>? id,
    Value<String>? type,
    Value<String>? payload,
    Value<String>? createdAt,
  }) {
    return PendingEventsCompanion(
      id: id ?? this.id,
      type: type ?? this.type,
      payload: payload ?? this.payload,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (type.present) {
      map['type'] = Variable<String>(type.value);
    }
    if (payload.present) {
      map['payload'] = Variable<String>(payload.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('PendingEventsCompanion(')
          ..write('id: $id, ')
          ..write('type: $type, ')
          ..write('payload: $payload, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

class $SyncMetaTable extends SyncMeta
    with TableInfo<$SyncMetaTable, SyncMetaEntry> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SyncMetaTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _keyMeta = const VerificationMeta('key');
  @override
  late final GeneratedColumn<String> key = GeneratedColumn<String>(
    'key',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _valueMeta = const VerificationMeta('value');
  @override
  late final GeneratedColumn<String> value = GeneratedColumn<String>(
    'value',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [key, value];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'sync_meta';
  @override
  VerificationContext validateIntegrity(
    Insertable<SyncMetaEntry> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('key')) {
      context.handle(
        _keyMeta,
        key.isAcceptableOrUnknown(data['key']!, _keyMeta),
      );
    } else if (isInserting) {
      context.missing(_keyMeta);
    }
    if (data.containsKey('value')) {
      context.handle(
        _valueMeta,
        value.isAcceptableOrUnknown(data['value']!, _valueMeta),
      );
    } else if (isInserting) {
      context.missing(_valueMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {key};
  @override
  SyncMetaEntry map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SyncMetaEntry(
      key: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}key'],
      )!,
      value: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}value'],
      )!,
    );
  }

  @override
  $SyncMetaTable createAlias(String alias) {
    return $SyncMetaTable(attachedDatabase, alias);
  }
}

class SyncMetaEntry extends DataClass implements Insertable<SyncMetaEntry> {
  final String key;
  final String value;
  const SyncMetaEntry({required this.key, required this.value});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['key'] = Variable<String>(key);
    map['value'] = Variable<String>(value);
    return map;
  }

  SyncMetaCompanion toCompanion(bool nullToAbsent) {
    return SyncMetaCompanion(key: Value(key), value: Value(value));
  }

  factory SyncMetaEntry.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SyncMetaEntry(
      key: serializer.fromJson<String>(json['key']),
      value: serializer.fromJson<String>(json['value']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'key': serializer.toJson<String>(key),
      'value': serializer.toJson<String>(value),
    };
  }

  SyncMetaEntry copyWith({String? key, String? value}) =>
      SyncMetaEntry(key: key ?? this.key, value: value ?? this.value);
  SyncMetaEntry copyWithCompanion(SyncMetaCompanion data) {
    return SyncMetaEntry(
      key: data.key.present ? data.key.value : this.key,
      value: data.value.present ? data.value.value : this.value,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SyncMetaEntry(')
          ..write('key: $key, ')
          ..write('value: $value')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(key, value);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SyncMetaEntry &&
          other.key == this.key &&
          other.value == this.value);
}

class SyncMetaCompanion extends UpdateCompanion<SyncMetaEntry> {
  final Value<String> key;
  final Value<String> value;
  final Value<int> rowid;
  const SyncMetaCompanion({
    this.key = const Value.absent(),
    this.value = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  SyncMetaCompanion.insert({
    required String key,
    required String value,
    this.rowid = const Value.absent(),
  }) : key = Value(key),
       value = Value(value);
  static Insertable<SyncMetaEntry> custom({
    Expression<String>? key,
    Expression<String>? value,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (key != null) 'key': key,
      if (value != null) 'value': value,
      if (rowid != null) 'rowid': rowid,
    });
  }

  SyncMetaCompanion copyWith({
    Value<String>? key,
    Value<String>? value,
    Value<int>? rowid,
  }) {
    return SyncMetaCompanion(
      key: key ?? this.key,
      value: value ?? this.value,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (key.present) {
      map['key'] = Variable<String>(key.value);
    }
    if (value.present) {
      map['value'] = Variable<String>(value.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SyncMetaCompanion(')
          ..write('key: $key, ')
          ..write('value: $value, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDb extends GeneratedDatabase {
  _$AppDb(QueryExecutor e) : super(e);
  $AppDbManager get managers => $AppDbManager(this);
  late final $TopicsTable topics = $TopicsTable(this);
  late final $LessonsTable lessons = $LessonsTable(this);
  late final $SentencesTable sentences = $SentencesTable(this);
  late final $WordsTable words = $WordsTable(this);
  late final $LessonWordsTable lessonWords = $LessonWordsTable(this);
  late final $HskWordsTable hskWords = $HskWordsTable(this);
  late final $PendingEventsTable pendingEvents = $PendingEventsTable(this);
  late final $SyncMetaTable syncMeta = $SyncMetaTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    topics,
    lessons,
    sentences,
    words,
    lessonWords,
    hskWords,
    pendingEvents,
    syncMeta,
  ];
}

typedef $$TopicsTableCreateCompanionBuilder = TopicsCompanion Function({
  Value<int> id,
  required String name,
  required int orderIndex,
  required String createdAt,
});
typedef $$TopicsTableUpdateCompanionBuilder = TopicsCompanion Function({
  Value<int> id,
  Value<String> name,
  Value<int> orderIndex,
  Value<String> createdAt,
});

class $$TopicsTableFilterComposer extends Composer<_$AppDb, $TopicsTable> {
  $$TopicsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get orderIndex => $composableBuilder(
    column: $table.orderIndex,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$TopicsTableOrderingComposer extends Composer<_$AppDb, $TopicsTable> {
  $$TopicsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get orderIndex => $composableBuilder(
    column: $table.orderIndex,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$TopicsTableAnnotationComposer extends Composer<_$AppDb, $TopicsTable> {
  $$TopicsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get name =>
      $composableBuilder(column: $table.name, builder: (column) => column);

  GeneratedColumn<int> get orderIndex => $composableBuilder(
    column: $table.orderIndex,
    builder: (column) => column,
  );

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$TopicsTableTableManager
    extends
        RootTableManager<
          _$AppDb,
          $TopicsTable,
          Topic,
          $$TopicsTableFilterComposer,
          $$TopicsTableOrderingComposer,
          $$TopicsTableAnnotationComposer,
          $$TopicsTableCreateCompanionBuilder,
          $$TopicsTableUpdateCompanionBuilder,
          (Topic, BaseReferences<_$AppDb, $TopicsTable, Topic>),
          Topic,
          PrefetchHooks Function()
        > {
  $$TopicsTableTableManager(_$AppDb db, $TopicsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$TopicsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$TopicsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$TopicsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> name = const Value.absent(),
                Value<int> orderIndex = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
              }) => TopicsCompanion(
                id: id,
                name: name,
                orderIndex: orderIndex,
                createdAt: createdAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String name,
                required int orderIndex,
                required String createdAt,
              }) => TopicsCompanion.insert(
                id: id,
                name: name,
                orderIndex: orderIndex,
                createdAt: createdAt,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$TopicsTable, Topic>(table),
                  BaseReferences<_$AppDb, $TopicsTable, Topic>(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$TopicsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDb,
      $TopicsTable,
      Topic,
      $$TopicsTableFilterComposer,
      $$TopicsTableOrderingComposer,
      $$TopicsTableAnnotationComposer,
      $$TopicsTableCreateCompanionBuilder,
      $$TopicsTableUpdateCompanionBuilder,
      (Topic, BaseReferences<_$AppDb, $TopicsTable, Topic>),
      Topic,
      PrefetchHooks Function()
    >;
typedef $$LessonsTableCreateCompanionBuilder = LessonsCompanion Function({
  Value<int> id,
  required int topicId,
  required int orderIndex,
  Value<String?> title,
  required String status,
  Value<String?> audioPath,
  required String createdAt,
  Value<String?> lastReviewedAt,
});
typedef $$LessonsTableUpdateCompanionBuilder = LessonsCompanion Function({
  Value<int> id,
  Value<int> topicId,
  Value<int> orderIndex,
  Value<String?> title,
  Value<String> status,
  Value<String?> audioPath,
  Value<String> createdAt,
  Value<String?> lastReviewedAt,
});

class $$LessonsTableFilterComposer extends Composer<_$AppDb, $LessonsTable> {
  $$LessonsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get topicId => $composableBuilder(
    column: $table.topicId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get orderIndex => $composableBuilder(
    column: $table.orderIndex,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get audioPath => $composableBuilder(
    column: $table.audioPath,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get lastReviewedAt => $composableBuilder(
    column: $table.lastReviewedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$LessonsTableOrderingComposer extends Composer<_$AppDb, $LessonsTable> {
  $$LessonsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get topicId => $composableBuilder(
    column: $table.topicId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get orderIndex => $composableBuilder(
    column: $table.orderIndex,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get audioPath => $composableBuilder(
    column: $table.audioPath,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get lastReviewedAt => $composableBuilder(
    column: $table.lastReviewedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$LessonsTableAnnotationComposer
    extends Composer<_$AppDb, $LessonsTable> {
  $$LessonsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get topicId =>
      $composableBuilder(column: $table.topicId, builder: (column) => column);

  GeneratedColumn<int> get orderIndex => $composableBuilder(
    column: $table.orderIndex,
    builder: (column) => column,
  );

  GeneratedColumn<String> get title =>
      $composableBuilder(column: $table.title, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<String> get audioPath =>
      $composableBuilder(column: $table.audioPath, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<String> get lastReviewedAt => $composableBuilder(
    column: $table.lastReviewedAt,
    builder: (column) => column,
  );
}

class $$LessonsTableTableManager
    extends
        RootTableManager<
          _$AppDb,
          $LessonsTable,
          Lesson,
          $$LessonsTableFilterComposer,
          $$LessonsTableOrderingComposer,
          $$LessonsTableAnnotationComposer,
          $$LessonsTableCreateCompanionBuilder,
          $$LessonsTableUpdateCompanionBuilder,
          (Lesson, BaseReferences<_$AppDb, $LessonsTable, Lesson>),
          Lesson,
          PrefetchHooks Function()
        > {
  $$LessonsTableTableManager(_$AppDb db, $LessonsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$LessonsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$LessonsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$LessonsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> topicId = const Value.absent(),
                Value<int> orderIndex = const Value.absent(),
                Value<String?> title = const Value.absent(),
                Value<String> status = const Value.absent(),
                Value<String?> audioPath = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
                Value<String?> lastReviewedAt = const Value.absent(),
              }) => LessonsCompanion(
                id: id,
                topicId: topicId,
                orderIndex: orderIndex,
                title: title,
                status: status,
                audioPath: audioPath,
                createdAt: createdAt,
                lastReviewedAt: lastReviewedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int topicId,
                required int orderIndex,
                Value<String?> title = const Value.absent(),
                required String status,
                Value<String?> audioPath = const Value.absent(),
                required String createdAt,
                Value<String?> lastReviewedAt = const Value.absent(),
              }) => LessonsCompanion.insert(
                id: id,
                topicId: topicId,
                orderIndex: orderIndex,
                title: title,
                status: status,
                audioPath: audioPath,
                createdAt: createdAt,
                lastReviewedAt: lastReviewedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$LessonsTable, Lesson>(table),
                  BaseReferences<_$AppDb, $LessonsTable, Lesson>(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$LessonsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDb,
      $LessonsTable,
      Lesson,
      $$LessonsTableFilterComposer,
      $$LessonsTableOrderingComposer,
      $$LessonsTableAnnotationComposer,
      $$LessonsTableCreateCompanionBuilder,
      $$LessonsTableUpdateCompanionBuilder,
      (Lesson, BaseReferences<_$AppDb, $LessonsTable, Lesson>),
      Lesson,
      PrefetchHooks Function()
    >;
typedef $$SentencesTableCreateCompanionBuilder = SentencesCompanion Function({
  Value<int> id,
  required int lessonId,
  required int paraIndex,
  required int sentIndex,
  required String content,
  required String segmentation,
  Value<String?> translation,
});
typedef $$SentencesTableUpdateCompanionBuilder = SentencesCompanion Function({
  Value<int> id,
  Value<int> lessonId,
  Value<int> paraIndex,
  Value<int> sentIndex,
  Value<String> content,
  Value<String> segmentation,
  Value<String?> translation,
});

class $$SentencesTableFilterComposer
    extends Composer<_$AppDb, $SentencesTable> {
  $$SentencesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get lessonId => $composableBuilder(
    column: $table.lessonId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get paraIndex => $composableBuilder(
    column: $table.paraIndex,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get sentIndex => $composableBuilder(
    column: $table.sentIndex,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get content => $composableBuilder(
    column: $table.content,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get segmentation => $composableBuilder(
    column: $table.segmentation,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get translation => $composableBuilder(
    column: $table.translation,
    builder: (column) => ColumnFilters(column),
  );
}

class $$SentencesTableOrderingComposer
    extends Composer<_$AppDb, $SentencesTable> {
  $$SentencesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get lessonId => $composableBuilder(
    column: $table.lessonId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get paraIndex => $composableBuilder(
    column: $table.paraIndex,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get sentIndex => $composableBuilder(
    column: $table.sentIndex,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get content => $composableBuilder(
    column: $table.content,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get segmentation => $composableBuilder(
    column: $table.segmentation,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get translation => $composableBuilder(
    column: $table.translation,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$SentencesTableAnnotationComposer
    extends Composer<_$AppDb, $SentencesTable> {
  $$SentencesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get lessonId =>
      $composableBuilder(column: $table.lessonId, builder: (column) => column);

  GeneratedColumn<int> get paraIndex =>
      $composableBuilder(column: $table.paraIndex, builder: (column) => column);

  GeneratedColumn<int> get sentIndex =>
      $composableBuilder(column: $table.sentIndex, builder: (column) => column);

  GeneratedColumn<String> get content =>
      $composableBuilder(column: $table.content, builder: (column) => column);

  GeneratedColumn<String> get segmentation => $composableBuilder(
    column: $table.segmentation,
    builder: (column) => column,
  );

  GeneratedColumn<String> get translation => $composableBuilder(
    column: $table.translation,
    builder: (column) => column,
  );
}

class $$SentencesTableTableManager
    extends
        RootTableManager<
          _$AppDb,
          $SentencesTable,
          Sentence,
          $$SentencesTableFilterComposer,
          $$SentencesTableOrderingComposer,
          $$SentencesTableAnnotationComposer,
          $$SentencesTableCreateCompanionBuilder,
          $$SentencesTableUpdateCompanionBuilder,
          (Sentence, BaseReferences<_$AppDb, $SentencesTable, Sentence>),
          Sentence,
          PrefetchHooks Function()
        > {
  $$SentencesTableTableManager(_$AppDb db, $SentencesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$SentencesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$SentencesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$SentencesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> lessonId = const Value.absent(),
                Value<int> paraIndex = const Value.absent(),
                Value<int> sentIndex = const Value.absent(),
                Value<String> content = const Value.absent(),
                Value<String> segmentation = const Value.absent(),
                Value<String?> translation = const Value.absent(),
              }) => SentencesCompanion(
                id: id,
                lessonId: lessonId,
                paraIndex: paraIndex,
                sentIndex: sentIndex,
                content: content,
                segmentation: segmentation,
                translation: translation,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int lessonId,
                required int paraIndex,
                required int sentIndex,
                required String content,
                required String segmentation,
                Value<String?> translation = const Value.absent(),
              }) => SentencesCompanion.insert(
                id: id,
                lessonId: lessonId,
                paraIndex: paraIndex,
                sentIndex: sentIndex,
                content: content,
                segmentation: segmentation,
                translation: translation,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$SentencesTable, Sentence>(table),
                  BaseReferences<_$AppDb, $SentencesTable, Sentence>(
                    db,
                    table,
                    e,
                  ),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$SentencesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDb,
      $SentencesTable,
      Sentence,
      $$SentencesTableFilterComposer,
      $$SentencesTableOrderingComposer,
      $$SentencesTableAnnotationComposer,
      $$SentencesTableCreateCompanionBuilder,
      $$SentencesTableUpdateCompanionBuilder,
      (Sentence, BaseReferences<_$AppDb, $SentencesTable, Sentence>),
      Sentence,
      PrefetchHooks Function()
    >;
typedef $$WordsTableCreateCompanionBuilder = WordsCompanion Function({
  Value<int> id,
  required String word,
  Value<String?> pinyin,
  Value<String?> definition,
  required String listState,
  Value<int?> hskWordId,
  required String source,
  required String addedAt,
  Value<double> ease,
  Value<double?> intervalDays,
  Value<String?> dueAt,
  Value<int> reps,
  Value<int> lapses,
  Value<String?> lastRatedAt,
});
typedef $$WordsTableUpdateCompanionBuilder = WordsCompanion Function({
  Value<int> id,
  Value<String> word,
  Value<String?> pinyin,
  Value<String?> definition,
  Value<String> listState,
  Value<int?> hskWordId,
  Value<String> source,
  Value<String> addedAt,
  Value<double> ease,
  Value<double?> intervalDays,
  Value<String?> dueAt,
  Value<int> reps,
  Value<int> lapses,
  Value<String?> lastRatedAt,
});

class $$WordsTableFilterComposer extends Composer<_$AppDb, $WordsTable> {
  $$WordsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get word => $composableBuilder(
    column: $table.word,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get pinyin => $composableBuilder(
    column: $table.pinyin,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get definition => $composableBuilder(
    column: $table.definition,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get listState => $composableBuilder(
    column: $table.listState,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get hskWordId => $composableBuilder(
    column: $table.hskWordId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get source => $composableBuilder(
    column: $table.source,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get addedAt => $composableBuilder(
    column: $table.addedAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get ease => $composableBuilder(
    column: $table.ease,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get intervalDays => $composableBuilder(
    column: $table.intervalDays,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get dueAt => $composableBuilder(
    column: $table.dueAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get reps => $composableBuilder(
    column: $table.reps,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get lapses => $composableBuilder(
    column: $table.lapses,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get lastRatedAt => $composableBuilder(
    column: $table.lastRatedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$WordsTableOrderingComposer extends Composer<_$AppDb, $WordsTable> {
  $$WordsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get word => $composableBuilder(
    column: $table.word,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get pinyin => $composableBuilder(
    column: $table.pinyin,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get definition => $composableBuilder(
    column: $table.definition,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get listState => $composableBuilder(
    column: $table.listState,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get hskWordId => $composableBuilder(
    column: $table.hskWordId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get source => $composableBuilder(
    column: $table.source,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get addedAt => $composableBuilder(
    column: $table.addedAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get ease => $composableBuilder(
    column: $table.ease,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get intervalDays => $composableBuilder(
    column: $table.intervalDays,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get dueAt => $composableBuilder(
    column: $table.dueAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get reps => $composableBuilder(
    column: $table.reps,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get lapses => $composableBuilder(
    column: $table.lapses,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get lastRatedAt => $composableBuilder(
    column: $table.lastRatedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$WordsTableAnnotationComposer extends Composer<_$AppDb, $WordsTable> {
  $$WordsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get word =>
      $composableBuilder(column: $table.word, builder: (column) => column);

  GeneratedColumn<String> get pinyin =>
      $composableBuilder(column: $table.pinyin, builder: (column) => column);

  GeneratedColumn<String> get definition => $composableBuilder(
    column: $table.definition,
    builder: (column) => column,
  );

  GeneratedColumn<String> get listState =>
      $composableBuilder(column: $table.listState, builder: (column) => column);

  GeneratedColumn<int> get hskWordId =>
      $composableBuilder(column: $table.hskWordId, builder: (column) => column);

  GeneratedColumn<String> get source =>
      $composableBuilder(column: $table.source, builder: (column) => column);

  GeneratedColumn<String> get addedAt =>
      $composableBuilder(column: $table.addedAt, builder: (column) => column);

  GeneratedColumn<double> get ease =>
      $composableBuilder(column: $table.ease, builder: (column) => column);

  GeneratedColumn<double> get intervalDays => $composableBuilder(
    column: $table.intervalDays,
    builder: (column) => column,
  );

  GeneratedColumn<String> get dueAt =>
      $composableBuilder(column: $table.dueAt, builder: (column) => column);

  GeneratedColumn<int> get reps =>
      $composableBuilder(column: $table.reps, builder: (column) => column);

  GeneratedColumn<int> get lapses =>
      $composableBuilder(column: $table.lapses, builder: (column) => column);

  GeneratedColumn<String> get lastRatedAt => $composableBuilder(
    column: $table.lastRatedAt,
    builder: (column) => column,
  );
}

class $$WordsTableTableManager
    extends
        RootTableManager<
          _$AppDb,
          $WordsTable,
          Word,
          $$WordsTableFilterComposer,
          $$WordsTableOrderingComposer,
          $$WordsTableAnnotationComposer,
          $$WordsTableCreateCompanionBuilder,
          $$WordsTableUpdateCompanionBuilder,
          (Word, BaseReferences<_$AppDb, $WordsTable, Word>),
          Word,
          PrefetchHooks Function()
        > {
  $$WordsTableTableManager(_$AppDb db, $WordsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$WordsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$WordsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$WordsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> word = const Value.absent(),
                Value<String?> pinyin = const Value.absent(),
                Value<String?> definition = const Value.absent(),
                Value<String> listState = const Value.absent(),
                Value<int?> hskWordId = const Value.absent(),
                Value<String> source = const Value.absent(),
                Value<String> addedAt = const Value.absent(),
                Value<double> ease = const Value.absent(),
                Value<double?> intervalDays = const Value.absent(),
                Value<String?> dueAt = const Value.absent(),
                Value<int> reps = const Value.absent(),
                Value<int> lapses = const Value.absent(),
                Value<String?> lastRatedAt = const Value.absent(),
              }) => WordsCompanion(
                id: id,
                word: word,
                pinyin: pinyin,
                definition: definition,
                listState: listState,
                hskWordId: hskWordId,
                source: source,
                addedAt: addedAt,
                ease: ease,
                intervalDays: intervalDays,
                dueAt: dueAt,
                reps: reps,
                lapses: lapses,
                lastRatedAt: lastRatedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String word,
                Value<String?> pinyin = const Value.absent(),
                Value<String?> definition = const Value.absent(),
                required String listState,
                Value<int?> hskWordId = const Value.absent(),
                required String source,
                required String addedAt,
                Value<double> ease = const Value.absent(),
                Value<double?> intervalDays = const Value.absent(),
                Value<String?> dueAt = const Value.absent(),
                Value<int> reps = const Value.absent(),
                Value<int> lapses = const Value.absent(),
                Value<String?> lastRatedAt = const Value.absent(),
              }) => WordsCompanion.insert(
                id: id,
                word: word,
                pinyin: pinyin,
                definition: definition,
                listState: listState,
                hskWordId: hskWordId,
                source: source,
                addedAt: addedAt,
                ease: ease,
                intervalDays: intervalDays,
                dueAt: dueAt,
                reps: reps,
                lapses: lapses,
                lastRatedAt: lastRatedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$WordsTable, Word>(table),
                  BaseReferences<_$AppDb, $WordsTable, Word>(db, table, e),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$WordsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDb,
      $WordsTable,
      Word,
      $$WordsTableFilterComposer,
      $$WordsTableOrderingComposer,
      $$WordsTableAnnotationComposer,
      $$WordsTableCreateCompanionBuilder,
      $$WordsTableUpdateCompanionBuilder,
      (Word, BaseReferences<_$AppDb, $WordsTable, Word>),
      Word,
      PrefetchHooks Function()
    >;
typedef $$LessonWordsTableCreateCompanionBuilder =
    LessonWordsCompanion Function({
      required int lessonId,
      required int wordId,
      required String role,
      Value<int> rowid,
    });
typedef $$LessonWordsTableUpdateCompanionBuilder =
    LessonWordsCompanion Function({
      Value<int> lessonId,
      Value<int> wordId,
      Value<String> role,
      Value<int> rowid,
    });

class $$LessonWordsTableFilterComposer
    extends Composer<_$AppDb, $LessonWordsTable> {
  $$LessonWordsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get lessonId => $composableBuilder(
    column: $table.lessonId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get wordId => $composableBuilder(
    column: $table.wordId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get role => $composableBuilder(
    column: $table.role,
    builder: (column) => ColumnFilters(column),
  );
}

class $$LessonWordsTableOrderingComposer
    extends Composer<_$AppDb, $LessonWordsTable> {
  $$LessonWordsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get lessonId => $composableBuilder(
    column: $table.lessonId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get wordId => $composableBuilder(
    column: $table.wordId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get role => $composableBuilder(
    column: $table.role,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$LessonWordsTableAnnotationComposer
    extends Composer<_$AppDb, $LessonWordsTable> {
  $$LessonWordsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get lessonId =>
      $composableBuilder(column: $table.lessonId, builder: (column) => column);

  GeneratedColumn<int> get wordId =>
      $composableBuilder(column: $table.wordId, builder: (column) => column);

  GeneratedColumn<String> get role =>
      $composableBuilder(column: $table.role, builder: (column) => column);
}

class $$LessonWordsTableTableManager
    extends
        RootTableManager<
          _$AppDb,
          $LessonWordsTable,
          LessonWord,
          $$LessonWordsTableFilterComposer,
          $$LessonWordsTableOrderingComposer,
          $$LessonWordsTableAnnotationComposer,
          $$LessonWordsTableCreateCompanionBuilder,
          $$LessonWordsTableUpdateCompanionBuilder,
          (LessonWord, BaseReferences<_$AppDb, $LessonWordsTable, LessonWord>),
          LessonWord,
          PrefetchHooks Function()
        > {
  $$LessonWordsTableTableManager(_$AppDb db, $LessonWordsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$LessonWordsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$LessonWordsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$LessonWordsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> lessonId = const Value.absent(),
                Value<int> wordId = const Value.absent(),
                Value<String> role = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => LessonWordsCompanion(
                lessonId: lessonId,
                wordId: wordId,
                role: role,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required int lessonId,
                required int wordId,
                required String role,
                Value<int> rowid = const Value.absent(),
              }) => LessonWordsCompanion.insert(
                lessonId: lessonId,
                wordId: wordId,
                role: role,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$LessonWordsTable, LessonWord>(table),
                  BaseReferences<_$AppDb, $LessonWordsTable, LessonWord>(
                    db,
                    table,
                    e,
                  ),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$LessonWordsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDb,
      $LessonWordsTable,
      LessonWord,
      $$LessonWordsTableFilterComposer,
      $$LessonWordsTableOrderingComposer,
      $$LessonWordsTableAnnotationComposer,
      $$LessonWordsTableCreateCompanionBuilder,
      $$LessonWordsTableUpdateCompanionBuilder,
      (LessonWord, BaseReferences<_$AppDb, $LessonWordsTable, LessonWord>),
      LessonWord,
      PrefetchHooks Function()
    >;
typedef $$HskWordsTableCreateCompanionBuilder = HskWordsCompanion Function({
  Value<int> id,
  required String word,
  Value<String?> pinyin,
  Value<String?> definition,
  required int level,
  required String appState,
});
typedef $$HskWordsTableUpdateCompanionBuilder = HskWordsCompanion Function({
  Value<int> id,
  Value<String> word,
  Value<String?> pinyin,
  Value<String?> definition,
  Value<int> level,
  Value<String> appState,
});

class $$HskWordsTableFilterComposer extends Composer<_$AppDb, $HskWordsTable> {
  $$HskWordsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get word => $composableBuilder(
    column: $table.word,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get pinyin => $composableBuilder(
    column: $table.pinyin,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get definition => $composableBuilder(
    column: $table.definition,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get level => $composableBuilder(
    column: $table.level,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get appState => $composableBuilder(
    column: $table.appState,
    builder: (column) => ColumnFilters(column),
  );
}

class $$HskWordsTableOrderingComposer
    extends Composer<_$AppDb, $HskWordsTable> {
  $$HskWordsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get word => $composableBuilder(
    column: $table.word,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get pinyin => $composableBuilder(
    column: $table.pinyin,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get definition => $composableBuilder(
    column: $table.definition,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get level => $composableBuilder(
    column: $table.level,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get appState => $composableBuilder(
    column: $table.appState,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$HskWordsTableAnnotationComposer
    extends Composer<_$AppDb, $HskWordsTable> {
  $$HskWordsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get word =>
      $composableBuilder(column: $table.word, builder: (column) => column);

  GeneratedColumn<String> get pinyin =>
      $composableBuilder(column: $table.pinyin, builder: (column) => column);

  GeneratedColumn<String> get definition => $composableBuilder(
    column: $table.definition,
    builder: (column) => column,
  );

  GeneratedColumn<int> get level =>
      $composableBuilder(column: $table.level, builder: (column) => column);

  GeneratedColumn<String> get appState =>
      $composableBuilder(column: $table.appState, builder: (column) => column);
}

class $$HskWordsTableTableManager
    extends
        RootTableManager<
          _$AppDb,
          $HskWordsTable,
          HskWord,
          $$HskWordsTableFilterComposer,
          $$HskWordsTableOrderingComposer,
          $$HskWordsTableAnnotationComposer,
          $$HskWordsTableCreateCompanionBuilder,
          $$HskWordsTableUpdateCompanionBuilder,
          (HskWord, BaseReferences<_$AppDb, $HskWordsTable, HskWord>),
          HskWord,
          PrefetchHooks Function()
        > {
  $$HskWordsTableTableManager(_$AppDb db, $HskWordsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$HskWordsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$HskWordsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$HskWordsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> word = const Value.absent(),
                Value<String?> pinyin = const Value.absent(),
                Value<String?> definition = const Value.absent(),
                Value<int> level = const Value.absent(),
                Value<String> appState = const Value.absent(),
              }) => HskWordsCompanion(
                id: id,
                word: word,
                pinyin: pinyin,
                definition: definition,
                level: level,
                appState: appState,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String word,
                Value<String?> pinyin = const Value.absent(),
                Value<String?> definition = const Value.absent(),
                required int level,
                required String appState,
              }) => HskWordsCompanion.insert(
                id: id,
                word: word,
                pinyin: pinyin,
                definition: definition,
                level: level,
                appState: appState,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$HskWordsTable, HskWord>(table),
                  BaseReferences<_$AppDb, $HskWordsTable, HskWord>(
                    db,
                    table,
                    e,
                  ),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$HskWordsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDb,
      $HskWordsTable,
      HskWord,
      $$HskWordsTableFilterComposer,
      $$HskWordsTableOrderingComposer,
      $$HskWordsTableAnnotationComposer,
      $$HskWordsTableCreateCompanionBuilder,
      $$HskWordsTableUpdateCompanionBuilder,
      (HskWord, BaseReferences<_$AppDb, $HskWordsTable, HskWord>),
      HskWord,
      PrefetchHooks Function()
    >;
typedef $$PendingEventsTableCreateCompanionBuilder =
    PendingEventsCompanion Function({
      Value<int> id,
      required String type,
      required String payload,
      required String createdAt,
    });
typedef $$PendingEventsTableUpdateCompanionBuilder =
    PendingEventsCompanion Function({
      Value<int> id,
      Value<String> type,
      Value<String> payload,
      Value<String> createdAt,
    });

class $$PendingEventsTableFilterComposer
    extends Composer<_$AppDb, $PendingEventsTable> {
  $$PendingEventsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get type => $composableBuilder(
    column: $table.type,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get payload => $composableBuilder(
    column: $table.payload,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$PendingEventsTableOrderingComposer
    extends Composer<_$AppDb, $PendingEventsTable> {
  $$PendingEventsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get type => $composableBuilder(
    column: $table.type,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get payload => $composableBuilder(
    column: $table.payload,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$PendingEventsTableAnnotationComposer
    extends Composer<_$AppDb, $PendingEventsTable> {
  $$PendingEventsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get type =>
      $composableBuilder(column: $table.type, builder: (column) => column);

  GeneratedColumn<String> get payload =>
      $composableBuilder(column: $table.payload, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$PendingEventsTableTableManager
    extends
        RootTableManager<
          _$AppDb,
          $PendingEventsTable,
          PendingEvent,
          $$PendingEventsTableFilterComposer,
          $$PendingEventsTableOrderingComposer,
          $$PendingEventsTableAnnotationComposer,
          $$PendingEventsTableCreateCompanionBuilder,
          $$PendingEventsTableUpdateCompanionBuilder,
          (
            PendingEvent,
            BaseReferences<_$AppDb, $PendingEventsTable, PendingEvent>,
          ),
          PendingEvent,
          PrefetchHooks Function()
        > {
  $$PendingEventsTableTableManager(_$AppDb db, $PendingEventsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$PendingEventsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$PendingEventsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$PendingEventsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> type = const Value.absent(),
                Value<String> payload = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
              }) => PendingEventsCompanion(
                id: id,
                type: type,
                payload: payload,
                createdAt: createdAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String type,
                required String payload,
                required String createdAt,
              }) => PendingEventsCompanion.insert(
                id: id,
                type: type,
                payload: payload,
                createdAt: createdAt,
              ),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$PendingEventsTable, PendingEvent>(table),
                  BaseReferences<_$AppDb, $PendingEventsTable, PendingEvent>(
                    db,
                    table,
                    e,
                  ),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$PendingEventsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDb,
      $PendingEventsTable,
      PendingEvent,
      $$PendingEventsTableFilterComposer,
      $$PendingEventsTableOrderingComposer,
      $$PendingEventsTableAnnotationComposer,
      $$PendingEventsTableCreateCompanionBuilder,
      $$PendingEventsTableUpdateCompanionBuilder,
      (
        PendingEvent,
        BaseReferences<_$AppDb, $PendingEventsTable, PendingEvent>,
      ),
      PendingEvent,
      PrefetchHooks Function()
    >;
typedef $$SyncMetaTableCreateCompanionBuilder = SyncMetaCompanion Function({
  required String key,
  required String value,
  Value<int> rowid,
});
typedef $$SyncMetaTableUpdateCompanionBuilder = SyncMetaCompanion Function({
  Value<String> key,
  Value<String> value,
  Value<int> rowid,
});

class $$SyncMetaTableFilterComposer extends Composer<_$AppDb, $SyncMetaTable> {
  $$SyncMetaTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get key => $composableBuilder(
    column: $table.key,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get value => $composableBuilder(
    column: $table.value,
    builder: (column) => ColumnFilters(column),
  );
}

class $$SyncMetaTableOrderingComposer
    extends Composer<_$AppDb, $SyncMetaTable> {
  $$SyncMetaTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get key => $composableBuilder(
    column: $table.key,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get value => $composableBuilder(
    column: $table.value,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$SyncMetaTableAnnotationComposer
    extends Composer<_$AppDb, $SyncMetaTable> {
  $$SyncMetaTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get key =>
      $composableBuilder(column: $table.key, builder: (column) => column);

  GeneratedColumn<String> get value =>
      $composableBuilder(column: $table.value, builder: (column) => column);
}

class $$SyncMetaTableTableManager
    extends
        RootTableManager<
          _$AppDb,
          $SyncMetaTable,
          SyncMetaEntry,
          $$SyncMetaTableFilterComposer,
          $$SyncMetaTableOrderingComposer,
          $$SyncMetaTableAnnotationComposer,
          $$SyncMetaTableCreateCompanionBuilder,
          $$SyncMetaTableUpdateCompanionBuilder,
          (
            SyncMetaEntry,
            BaseReferences<_$AppDb, $SyncMetaTable, SyncMetaEntry>,
          ),
          SyncMetaEntry,
          PrefetchHooks Function()
        > {
  $$SyncMetaTableTableManager(_$AppDb db, $SyncMetaTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$SyncMetaTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$SyncMetaTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$SyncMetaTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback: ({
            Value<String> key = const Value.absent(),
            Value<String> value = const Value.absent(),
            Value<int> rowid = const Value.absent(),
          }) => SyncMetaCompanion(key: key, value: value, rowid: rowid),
          createCompanionCallback: ({
            required String key,
            required String value,
            Value<int> rowid = const Value.absent(),
          }) => SyncMetaCompanion.insert(key: key, value: value, rowid: rowid),
          withReferenceMapper: (p0) => p0
              .map(
                (e) => (
                  e.readTable<$SyncMetaTable, SyncMetaEntry>(table),
                  BaseReferences<_$AppDb, $SyncMetaTable, SyncMetaEntry>(
                    db,
                    table,
                    e,
                  ),
                ),
              )
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$SyncMetaTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDb,
      $SyncMetaTable,
      SyncMetaEntry,
      $$SyncMetaTableFilterComposer,
      $$SyncMetaTableOrderingComposer,
      $$SyncMetaTableAnnotationComposer,
      $$SyncMetaTableCreateCompanionBuilder,
      $$SyncMetaTableUpdateCompanionBuilder,
      (SyncMetaEntry, BaseReferences<_$AppDb, $SyncMetaTable, SyncMetaEntry>),
      SyncMetaEntry,
      PrefetchHooks Function()
    >;

class $AppDbManager {
  final _$AppDb _db;
  $AppDbManager(this._db);
  $$TopicsTableTableManager get topics =>
      $$TopicsTableTableManager(_db, _db.topics);
  $$LessonsTableTableManager get lessons =>
      $$LessonsTableTableManager(_db, _db.lessons);
  $$SentencesTableTableManager get sentences =>
      $$SentencesTableTableManager(_db, _db.sentences);
  $$WordsTableTableManager get words =>
      $$WordsTableTableManager(_db, _db.words);
  $$LessonWordsTableTableManager get lessonWords =>
      $$LessonWordsTableTableManager(_db, _db.lessonWords);
  $$HskWordsTableTableManager get hskWords =>
      $$HskWordsTableTableManager(_db, _db.hskWords);
  $$PendingEventsTableTableManager get pendingEvents =>
      $$PendingEventsTableTableManager(_db, _db.pendingEvents);
  $$SyncMetaTableTableManager get syncMeta =>
      $$SyncMetaTableTableManager(_db, _db.syncMeta);
}
